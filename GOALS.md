# skip goals doc

## High level

I want to produce a genuinely attractive book (and eventually set of books) that will sit in my bookshelf and be nice to take out and read.

Intermediate milestones:
* write an index and select articles for the first volume (maybe “greatest hits”)
* scrapes with correct formatting for reach document for the first volume
* rudimentary / bare-bones formatted version of the pdf
* Simple layout with backgroud images, fonts, background color for dialogues, bold etc (mirror the website)
* Flavor images
* Flowed layout with images

Mandatory technical components
* Claude or gpt or whatever needs to be able to capture images of the pdf and look at it visually to identify issues with the layout and formatting
* Claude needs to be able to read the pdf text to identify and remove control characters, markdown, etc
* Claude needs to be able to re run and iterate on the parsers

## Volume 1
follow this page https://scp-wiki.wikidot.com/archived:heritage-collection

## Related pages

An important thing to understand is which related pages to include as part
of scraping / building an scp. Every page will be wikidot-linked to many
other pages; you can see their names in the wikidot source code. Some of
these should be included whenever this scp article is included. This
decision cannot be automated nicely; you will need to think about it
case-by-case. Here are some general guidelines:
* Experiment logs about this scp (e.g. experiment log 123-xxx-xxx for
  scp-xxx): yes
* exploration logs: yes
* destruction attempts: yes
* cross-links to other articles (scp-xxxx): no
* lists of articles: no
* stories: usually no, with rare exceptions where the story is fundamental
  to understanding the object
* article/story hubs (e.g. "dust and blood"): no
* tag pages: no

we should track which related pages "go with" each article in a stable local
file or files that's checked in so you can cross-reference it and use it in
scripts in the future. But we will need to work out which related pages go
with which each article by hand. Humans will sometimes need to make
corrections here too so make sure the format is easy for both humans and
machines to edit.
