"""Media Exporter classes."""


import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generator, Iterable, List, Optional

from anki.collection import Collection, SearchNode
from anki.decks import DeckId
from anki.notes import Note


def get_note_media(
    col: Collection, note: Note, fields: Optional[List[str]] = None
) -> List[str]:
    "Return a list of used media files in `note`."
    if fields:
        field_values = [note[field] for field in fields]
    else:
        field_values = note.fields
    flds = "".join(field_values)
    return col.media.files_in_str(note.mid, flds)


class MediaExporter(ABC):
    """Abstract media exporter."""

    col: Collection
    field: str

    @abstractmethod
    def file_lists(self) -> Generator[list[str], None, None]:
        """Return a generator that yields a list of media files for each note that should be exported."""

    def export(
        self, folder: Optional[Path], exts: Optional[set] = None
    ) -> Iterable[tuple[int, list[str]]]:
        """
        Export media files in `self.did` to `folder`,
        including only files that has extensions in `exts` if `exts` is not None.
        Returns a generator that yields the total media files exported so far and filenames as they are exported.
        """

        media_dir = self.col.media.dir()
        seen = set()
        exported = set()
        for filenames in self.file_lists():
            for filename in filenames:
                if filename in seen:
                    continue
                seen.add(filename)
                if exts is not None and os.path.splitext(filename)[1][1:] not in exts:
                    continue
                src_path = os.path.join(media_dir, filename)
                if not os.path.exists(src_path):
                    continue
                dest_path = os.path.join(folder, filename)
                shutil.copyfile(src_path, dest_path)
                exported.add(filename)
            yield len(exported), filenames

    @abstractmethod
    def note_count(self) -> int:
        pass


class NoteMediaExporter(MediaExporter):
    """Exporter for a list of notes."""

    def __init__(
        self, col: Collection, notes: list[Note], fields: Optional[List[str]] = None
    ):
        self.col = col
        self.notes = notes
        self.fields = fields

    def file_lists(self) -> Generator[list[str], None, None]:
        "Return a generator that yields a list of media files for each note in `self.notes`"

        for note in self.notes:
            yield get_note_media(self.col, note, self.fields)

    def note_count(self) -> int:
        return len(self.notes)


class DeckMediaExporter(MediaExporter):
    "Exporter for all media in a deck."

    def __init__(
        self,
        col: Collection,
        did: DeckId,
        exclude_files: Optional[List[str]] = None,
    ):
        self.col = col
        self.did = did
        self.excluded_files = exclude_files or []

    def file_lists(self) -> Generator[list[str], None, None]:
        "Return a generator that yields a list of media files for each note in the deck with the ID `self.did`"
        search_params = [SearchNode(deck=self.col.decks.name(self.did))]
        search = self.col.build_search_string(*search_params)
        for nid in self.col.find_notes(search):
            note = self.col.get_note(nid)
            note_media = get_note_media(self.col, note)
            yield [f for f in note_media if f not in self.excluded_files]

    def note_count(self) -> int:
        return self.col.decks.card_count([DeckId(self.did)], include_subdecks=True)
