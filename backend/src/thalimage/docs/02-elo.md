# Ranking by vote (ELO)

Voting shows you two images from a collection and asks which you prefer.
Each vote adjusts both images' scores using the ELO system borrowed from
chess: beating a highly-rated image gains you more than beating a
low-rated one, and an upset moves both scores further than an expected
result does.

Scores start at 1500. The K-factor — how far a single vote can move a
score — is 32, the same value chess federations use for ordinary play.
A win against an equally-rated image is worth +16; a win against a much
stronger one approaches +32.

## Scores belong to a collection

An image's score is recorded against the collection it was voted in.
The same image can sit near the top of one collection and mid-pack in
another, which is the intent: "best of my landscapes" and "best of
everything" are different questions.

Voting is therefore not available on "All Images", which is virtual and
has no collection row to attach scores to.

## How pairs are chosen

Candidates are every image in the collection that is not deleted and not
archived, minus NSFW images unless you have chosen to show them, and
narrowed by the date, aspect-ratio and media-type filters set on the
collection. Those are sorted by how many matches each has already had,
and the quarter with the fewest matches becomes the pool. Two images are
then drawn from that pool at random.

**This under-favours new images, and it is worth knowing about.** Match
count decides whether an image enters the pool, but inside the pool
every image is equally likely to be drawn. In a collection of 885
images the pool is 221 images wide; if 24 of them have never been voted
on, a particular new image comes up about once in every 110 pairs — no
more often than one you have already seen five times. Adding a batch of
images does not noticeably increase how often you see them.

Pairs are also not matched by score. Two images drawn from the pool may
be far apart in rating, and a vote between them is largely predictable,
which carries less information than a close contest would.

Both are known limitations rather than intended behaviour. Weighting the
draw by inverse match count, and choosing the second image by rating
proximity, would address them.

## What "matches" counts

The match counter increments for both images on every vote, winner and
loser alike. It is a count of appearances that produced a result, not a
count of wins. An image with no row in the score table has never been
voted on and counts as zero.
