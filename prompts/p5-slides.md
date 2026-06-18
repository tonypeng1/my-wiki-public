Your task is to generate a Marp slide deck on the topic of: 
"{YOUR TOPIC HERE}"

1. Run the following command to find all wiki articles relevant to this topic
   (replace KEYWORD with the topic name; add more keywords as needed):

   bash scripts/search-index.sh KEYWORD [KEYWORD2 ...]

   Use the matching entries to identify which article files to read.
   If results are too few, broaden with related terms.
   If results are too many, add a second keyword to narrow them.

2. Read each relevant article in full.

3. Plan a slide deck structure of 8-12 slides that covers 
   the topic clearly and logically. Show me the planned 
   structure before writing the full deck.

4. Write the complete Marp slide deck and save it to:
   wiki/slides/{topic-name}-{YYYY-MM-DD}.md
   where {YYYY-MM-DD} is today's date.

   Read wiki/slides/_marp-template.md and copy its frontmatter exactly as the
   opening of the file.

   Follow these slide guidelines:
   - Slide 1: Title slide — add `<!-- _class: title -->` directly after the opening `---` of the slide, then the title as `# …` and subtitle as plain paragraphs
   - Slide 2: Agenda / what this deck covers
   - Middle slides: substance, one idea per slide
   - Use bullet points sparingly — prefer short sentences
   - Include a "Key Takeaways" slide near the end
   - Final slide: open questions or areas for further research
   - Each slide should have a clear, short title
   - Keep text per slide under 60 words

5. Add an entry for the slide deck to wiki/index.md.