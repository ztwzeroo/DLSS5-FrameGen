"""安装清单：记录装了什么、来源哈希与备份索引，支撑卸载还原。"""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_DIR = ".dlss-combo"
MANIFEST_NAME = "manifest.json"
VERSION = 1


@dataclass
class Manifest:
    version: int = VERSION
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    dlss_combo_version: str = ""
    dlssg: dict = field(default_factory=dict)
    files: list[dict] = field(default_factory=list)      # {path, sha256, origin}
    backups: list[dict] = field(default_factory=list)    # {original, saved_to}

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

    def record_backup(self, original: str, saved_to: str) -> None:
        self.backups.append({"original": original, "saved_to": saved_to})

    def save(self, game_dir: Path) -> Path:
        target_dir = game_dir / MANIFEST_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / MANIFEST_NAME
        target.write_text(
            json.dumps(
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
            ),
            encoding="utf-8",
        )
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

    @staticmethod
    def our_file_names(m: "Manifest") -> set[str]:
        return {f["path"] for f in m.files}
