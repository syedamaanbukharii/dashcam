"""The gallery window.

Shows saved captures as a scrollable grid of thumbnails with per-item open,
export and delete actions, all delegated to the
:class:`~gesturecam.gallery.service.GalleryService`.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

from ..errors import StorageError
from ..gallery.service import GalleryService
from ..logging_setup import get_logger
from ..storage.models import CaptureRecord
from . import theme

logger = get_logger(__name__)

_COLUMNS = 3
_THUMB = (180, 135)


class GalleryWindow(ctk.CTkToplevel):  # pragma: no cover - requires a display
    """Browse, open, export and delete captures."""

    def __init__(self, master: ctk.CTkBaseClass, gallery: GalleryService) -> None:
        super().__init__(master)
        self._gallery = gallery
        self._thumbs: list[ctk.CTkImage] = []  # keep references alive

        self.title("Gallery")
        self.geometry("680x560")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color=theme.SURFACE)
        header.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(header, text="Captures", font=theme.font(theme.TITLE_SIZE, bold=True)).pack(
            side="left", padx=theme.PAD_M, pady=theme.PAD_M
        )
        ctk.CTkButton(header, text="Refresh", width=90, command=self._reload).pack(
            side="right", padx=theme.PAD_M
        )

        self._grid = ctk.CTkScrollableFrame(self)
        self._grid.grid(row=1, column=0, sticky="nsew", padx=theme.PAD_M, pady=theme.PAD_M)
        for col in range(_COLUMNS):
            self._grid.grid_columnconfigure(col, weight=1)

        self._empty = ctk.CTkLabel(self, text="", font=theme.font(), text_color=theme.TEXT_MUTED)
        self._empty.grid(row=2, column=0, pady=theme.PAD_S)

        self._reload()

    def _reload(self) -> None:
        for child in self._grid.winfo_children():
            child.destroy()
        self._thumbs.clear()

        records = self._gallery.list_captures()
        if not records:
            self._empty.configure(text="No captures yet — strike a pose!")
            return
        self._empty.configure(text=f"{len(records)} capture(s)")

        for position, record in enumerate(records):
            row, col = divmod(position, _COLUMNS)
            self._build_card(record, row, col)

    def _build_card(self, record: CaptureRecord, row: int, col: int) -> None:
        card = ctk.CTkFrame(self._grid, fg_color=theme.SURFACE)
        card.grid(row=row, column=col, padx=theme.PAD_S, pady=theme.PAD_S, sticky="nsew")

        thumb = self._load_thumbnail(record)
        image_label = ctk.CTkLabel(card, text="", image=thumb)
        image_label.pack(padx=theme.PAD_S, pady=theme.PAD_S)
        self._thumbs.append(thumb)

        caption = f"{record.media_type} · score {record.score:.2f}"
        ctk.CTkLabel(card, text=caption, font=theme.font(theme.BODY_SIZE - 1)).pack()

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(pady=theme.PAD_S)
        ctk.CTkButton(actions, text="Open", width=56, command=lambda r=record: self._open(r)).grid(
            row=0, column=0, padx=2
        )
        ctk.CTkButton(
            actions, text="Export", width=64, command=lambda r=record: self._export(r)
        ).grid(row=0, column=1, padx=2)
        ctk.CTkButton(
            actions,
            text="Delete",
            width=64,
            fg_color=theme.ERROR,
            hover_color="#B91C1C",
            command=lambda r=record: self._delete(r),
        ).grid(row=0, column=2, padx=2)

    def _load_thumbnail(self, record: CaptureRecord) -> ctk.CTkImage:
        path = Path(record.path)
        try:
            if record.media_type == "photo" and path.exists():
                image = Image.open(path)
                image.thumbnail(_THUMB)
            else:
                image = self._placeholder(record.media_type.upper())
        except OSError:
            image = self._placeholder("MISSING")
        return ctk.CTkImage(light_image=image, dark_image=image, size=image.size)

    @staticmethod
    def _placeholder(text: str) -> Image.Image:
        image = Image.new("RGB", _THUMB, (31, 41, 55))
        return image

    def _open(self, record: CaptureRecord) -> None:
        try:
            self._gallery.open_in_viewer(record)
        except StorageError as exc:
            self._empty.configure(text=str(exc))

    def _export(self, record: CaptureRecord) -> None:
        destination = filedialog.askdirectory(title="Export to folder")
        if not destination:
            return
        try:
            target = self._gallery.export(record, Path(destination))
        except StorageError as exc:
            self._empty.configure(text=str(exc))
            return
        self._empty.configure(text=f"Exported to {target}")

    def _delete(self, record: CaptureRecord) -> None:
        try:
            self._gallery.delete(record)
        except StorageError as exc:
            self._empty.configure(text=str(exc))
            return
        self._reload()
