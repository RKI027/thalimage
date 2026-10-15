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

## Which images are ranked

A collection's ranking holds the images that have been voted on there,
are still in the collection, and are not deleted. Archived images keep
their place: setting an image aside does not move everyone else's rank.

An image removed from a collection drops out of its ranking but keeps
its score, which comes back if the image is added again. Images never
voted on are not ranked at all; sorting a grid by ELO places them at the
starting 1500.

Images with equal scores share a rank: an image's rank is one plus the
number of ranked images scored higher.

## The rankings page

**Rankings**, on a collection and on its vote page, lists the ranked
images from the top: rank, score, matches won and lost. Opened from the
vote page, its back link returns to voting. Opening an image walks the
ranking itself: the viewer's previous and next follow the order of the
list, and the back link returns to it. An archived image opens but has
no place in the walk, which skips archived images as the gallery does.

The rankings ignore the filters set on the collection. NSFW images are
left out of the list unless you have chosen to show them, but still
count in the ranks, so the ranks shown can skip a number.

## Voting statistics

The rankings page's **Stats** tab shows how voting has gone in the
collection. It covers the images voting can draw: the collection's images
that are not deleted and not archived, voted on or not. NSFW images count
whatever the NSFW setting, since leaving them out would skew the figures;
only their file names appear.

**Match fairness.** The histogram counts images by matches played,
against a balanced schedule: with the matches played so far spread
evenly, every image would sit within one match of the average, shown as
a band. The Gini coefficient sums the unevenness up in one number: 0
when every image has played as often as every other, approaching 1 when
a few images have played nearly every match. The Lorenz curve shows the
same thing: the share of all matches played by the least-played images,
against the share of images they are; an even schedule follows the
diagonal. Matches by rank shows whether images at the top and the bottom
are still being challenged.

**Score and confidence.** The score histogram shows how far voting has
spread the images from the starting 1500. Plotting score against matches
shows how settled each score is: an image with few matches has a score
one or two votes could still move a long way.

**Pairs.** How many of the possible pairs have met at least once, and how
many met more than once. The head-to-head grid shows the 20 best-ranked
images voting can draw, each cell the record of the row's image against
the column's. Archived images are left out, so the ranks on its edges
can skip a number.

Matches are the same counts the rankings show: every vote the image took
part in there, including against images since removed or deleted. The
pair figures count only meetings between two images that are both still
covered.

## An image's standing

The viewer's information panel shows where an image stands. Opened from
a collection it has been voted in, it shows the score, the rank ("12th
of 954", out of the collection's ranked images) and the matches won and
lost there; the compact panel shows only score and rank. The full panel
also lists the image's score and rank in every other collection that
ranks it.

## Filtering by ELO

A collection's filters include **ELO**: the top or bottom part of the
ranking, as a percentage. It is a percentage of the whole ranking, not
of what the other filters leave: "top 10%" picks the same images
whatever else is set, and adding a filter on shape shows the portraits
among them. The image count shows how many pass.

The cut takes the stated share rounded up, so the top 10% of 954 ranked
images is 96 images, and the top 1% of a small ranking is at least one.
When images at the edge share a score, which of them fall inside is
decided by a fixed but arbitrary order, so the count stays exact.
Images never voted on are never in the top or bottom part. Archived
images take their place in it but stay out of the grid, so the count
can fall short of the share: 91 for a top 10% of 96 holding 5 archived.

The filter applies to voting too, so voting can be confined to the top
of a ranking to settle its order. The vote page marks that it is
filtered.

## How pairs are chosen

Candidates are every image in the collection that is not deleted and not
archived, minus NSFW images unless you have chosen to show them, and
narrowed by the date, aspect-ratio, media-type and ELO filters set on
the collection. Those are sorted by how many matches each has already had,
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
