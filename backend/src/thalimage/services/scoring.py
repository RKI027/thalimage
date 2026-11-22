"""ELO score arithmetic, shared by voting and replaying votes."""

import sqlite3

K_FACTOR = 32
START_SCORE = 1500.0


def after_match(winner: float, loser: float) -> tuple[float, float]:
    """The winner's and the loser's scores after one match."""
    e_winner = 1.0 / (1.0 + 10.0 ** ((loser - winner) / 400.0))
    e_loser = 1.0 - e_winner
    return winner + K_FACTOR * (1.0 - e_winner), loser + K_FACTOR * (0.0 - e_loser)


def replay_scores(conn: sqlite3.Connection, collection_id: int) -> None:
    """Recompute the collection's scores from its votes, in the order they
    were cast, after votes were removed or moved to another image. An image
    left without votes has no score. Runs inside the caller's transaction;
    does not commit."""
    scores: dict[str, float] = {}
    matches: dict[str, int] = {}
    for vote in conn.execute(
        "SELECT winner_hash, loser_hash FROM votes WHERE collection_id = ? ORDER BY id",
        (collection_id,),
    ):
        winner, loser = vote["winner_hash"], vote["loser_hash"]
        scores[winner], scores[loser] = after_match(
            scores.get(winner, START_SCORE), scores.get(loser, START_SCORE)
        )
        matches[winner] = matches.get(winner, 0) + 1
        matches[loser] = matches.get(loser, 0) + 1
    conn.execute("DELETE FROM elo_scores WHERE collection_id = ?", (collection_id,))
    conn.executemany(
        "INSERT INTO elo_scores (content_hash, collection_id, score, matches) VALUES (?, ?, ?, ?)",
        [(h, collection_id, scores[h], matches[h]) for h in scores],
    )
