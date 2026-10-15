"""Which images a collection's ELO ranking holds."""

from dataclasses import dataclass
from typing import Literal, Optional


def ranked_sql(collection: str = "?") -> str:
    """SELECT content_hash, score, matches of the images ranked in the
    collection that `collection` (a placeholder or a correlated column)
    names: scored there, not deleted, and still members. Archived images
    stay ranked. Aliases are prefixed `rk_` so the query nests inside
    others without shadowing their names."""
    return f"""SELECT rk_e.content_hash, rk_e.score, rk_e.matches
        FROM elo_scores rk_e
        JOIN collections rk_c ON rk_c.id = rk_e.collection_id
        JOIN images rk_i ON rk_i.content_hash = rk_e.content_hash
        WHERE rk_e.collection_id = {collection} AND rk_i.deleted = 0
        AND {member_sql("rk_c", "rk_e.content_hash")}"""


def member_sql(collection: str, content_hash: str) -> str:
    """SQL condition: the image `content_hash` names is a member of the
    collection row aliased `collection`. Source presets hold no
    collection_images rows; their members are the source's images."""
    return f"""CASE {collection}.type WHEN 'source_preset'
            THEN EXISTS (SELECT 1 FROM image_locations mb_l
                WHERE mb_l.source_id = {collection}.source_id AND mb_l.content_hash = {content_hash})
            ELSE EXISTS (SELECT 1 FROM collection_images mb_ci
                WHERE mb_ci.collection_id = {collection}.id AND mb_ci.content_hash = {content_hash})
        END"""


@dataclass(frozen=True)
class EloCut:
    """The top or bottom `percent` of a collection's ranking."""

    collection_id: int
    end: Literal["top", "bottom"]
    percent: int


def elo_cut(
    collection_id: Optional[int], end: Literal["top", "bottom"], percent: Optional[int]
) -> Optional[EloCut]:
    """The cut a listing asks for; None without a percentage, or outside a
    collection, which has no ranking."""
    if collection_id is None or percent is None:
        return None
    return EloCut(collection_id, end, percent)


def in_cut_sql(cut: EloCut, hash_col: str = "content_hash") -> tuple[str, list[object]]:
    """SQL condition, with its values: the image falls in the cut. The cut
    holds the stated share of the ranked images rounded up, taken in the
    order a grid sorted by ELO shows them, so ties at the edge split the
    same way there."""
    order = "DESC" if cut.end == "top" else "ASC"
    ranked = ranked_sql()
    sql = (
        f"{hash_col} IN (SELECT content_hash FROM ({ranked})"
        f" ORDER BY score {order}, content_hash {order}"
        f" LIMIT ((SELECT COUNT(*) FROM ({ranked})) * ? + 99) / 100)"
    )
    return sql, [cut.collection_id, cut.collection_id, cut.percent]
