"""安装清单：记录装了什么、来源哈希与备份索引，支撑卸载还原。

安全规则（对应审查 A/B/C）：
- 只有 ALLOWED_FILENAMES 内的文件名可被本工具管理；路径必须相对且不出游戏目录
- 备份只能存放在 .dlss-combo/ 内
- schema 版本未知 → 拒绝执行任何破坏性操作
- 备份记录区分 kind: "pre-existing"（用户原文件，卸载时还原）与
  "ours-history"（本工具旧版本，仅供回滚，卸载时丢弃）
"""
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .proxy_select import PROXY_CANDIDATES

MANIFEST_DIR = ".dlss-combo"
MANIFEST_NAME = "manifest.json"
VERSION = 1
INI_NAME = "dlssg_sm86.ini"
ALLOWED_FILENAMES = set(PROXY_CANDIDATES) | {INI_NAME}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def safe_target(game_dir: Path, rel: str) -> Path:
    """把清单里的相对路径安全拼进游戏目录；越界/绝对路径/链接逃逸一律 ValueError。"""
    if not isinstance(rel, str) or not rel or rel.strip() == "":
        raise ValueError(f"manifest 非法路径: {rel!r}")
    p = Path(rel)
    if p.is_absolute():
        raise ValueError(f"manifest 拒绝绝对路径: {rel}")
    if ".." in p.parts:
        raise ValueError(f"manifest 拒绝父目录跳转: {rel}")
    target = game_dir / p
    if target.is_symlink():
        raise ValueError(f"manifest 拒绝符号链接: {rel}")
    resolved_root = game_dir.resolve()
    resolved = target.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"manifest 路径越界: {rel}")
    return target


@dataclass
class Manifest:
    version: int = VERSION
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    dlss_combo_version: str = ""
    dlssg: dict = field(default_factory=dict)
    files: list[dict] = field(default_factory=list)      # {path, sha256, origin}
    backups: list[dict] = field(default_factory=list)    # {original, saved_to, kind}

    @staticmethod
    def sha256_of(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    def record_file(self, path: str, sha256: str, origin: str) -> None:
        self.files = [f for f in self.files if f["path"] != path]
        self.files.append({"path": path, "sha256": sha256, "origin": origin})

    def record_backup(
        self,
        original: str,
        saved_to: str,
        kind: str = "pre-existing",
        sha256: str | None = None,
    ) -> None:
        entry: dict = {"original": original, "saved_to": saved_to, "kind": kind}
        if sha256:
            entry["sha256"] = sha256
        self.backups.append(entry)

    def save(self, game_dir: Path) -> Path:
        """原子写入：先写临时文件再 os.replace，失败不破坏旧清单。"""
        target_dir = game_dir / MANIFEST_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / MANIFEST_NAME
        payload = json.dumps(
            {
                "version": self.version,
                "created": self.created,
                "dlss_combo_version": self.dlss_combo_version,
                "dlssg": self.dlssg,
                "files": self.files,
                "backups": self.backups,
            },
            ensure_ascii=False,
            indent=2,
        )
        fd, name = tempfile.mkstemp(
            prefix=".dlsscombo-", suffix=".tmp", dir=str(target_dir)
        )
        tmp = Path(name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(payload)
            os.replace(tmp, target)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
        return target

    @classmethod
    def load(cls, game_dir: Path) -> "Manifest":
        target = game_dir / MANIFEST_DIR / MANIFEST_NAME
        if not target.is_file():
            raise FileNotFoundError(f"no manifest at {target}")
        data = json.loads(target.read_text(encoding="utf-8"))
        return cls(
            version=data.get("version", VERSION),
            created=data.get("created", ""),
            dlss_combo_version=data.get("dlss_combo_version", ""),
            dlssg=data.get("dlssg", {}),
            files=data.get("files", []),
            backups=data.get("backups", []),
        )

    def validate(self, game_dir: Path) -> None:
        """卸载/重装前必过：任何一项不合法即抛 ValueError，不做任何修改。"""
        if self.version != VERSION:
            raise ValueError(f"未知 manifest schema 版本 (version={self.version})，拒绝执行")
        for entry in self.files:
            path = entry.get("path")
            if path not in ALLOWED_FILENAMES:
                raise ValueError(f"manifest 管理了允许范围外的路径: {path!r}")
            if not _SHA256_RE.match(str(entry.get("sha256", ""))):
                raise ValueError(f"manifest 哈希格式非法: {path!r}")
            safe_target(game_dir, path)
        for b in self.backups:
            if b.get("original") not in ALLOWED_FILENAMES:
                raise ValueError(f"备份目标在允许范围外: {b.get('original')!r}")
            saved_to = str(b.get("saved_to", ""))
            saved_path = Path(saved_to)
            if saved_path.is_absolute() or ".." in saved_path.parts:
                raise ValueError(f"备份位置越界: {saved_to!r}")
            if MANIFEST_DIR not in saved_path.parts:
                raise ValueError(f"备份必须位于 {MANIFEST_DIR}/ 内: {saved_to!r}")
            safe_target(game_dir, saved_to)

    def verify(self, game_dir: Path) -> list[str]:
        """对比磁盘文件与记录哈希，返回问题清单（空 = 健康）。"""
        problems: list[str] = []
        for entry in self.files:
            p = game_dir / entry["path"]
            if not p.is_file():
                problems.append(f"missing: {entry['path']}")
            elif self.sha256_of(p) != entry["sha256"]:
                problems.append(f"hash mismatch: {entry['path']}")
        return problems

    def current_hash_matches(self, game_dir: Path, path: str) -> bool | None:
        """文件当前哈希是否与安装时一致；文件不存在返回 None。"""
        p = game_dir / path
        if not p.is_file():
            return None
        recorded = next((f["sha256"] for f in self.files if f["path"] == path), None)
        if recorded is None:
            return None
        return self.sha256_of(p) == recorded

    @staticmethod
    def our_file_names(m: "Manifest") -> set[str]:
        return {f["path"] for f in m.files}
