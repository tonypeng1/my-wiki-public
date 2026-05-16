Read INSTRUCTIONS.md first and follow all conventions defined there.

Your task is to generate a Marp slide deck on the topic of: 
"{YOUR TOPIC HERE}"

1. Read wiki/index.md to identify all wiki articles relevant 
   to this topic.

2. Read each relevant article in full.

3. Plan a slide deck structure of 8-12 slides that covers 
   the topic clearly and logically. Show me the planned 
   structure before writing the full deck.

4. Write the complete Marp slide deck and save it to:
   wiki/slides/{topic-name}.md

   The file must begin with this frontmatter (copy it exactly):
   ---
   marp: true
   theme: default
   paginate: true
   style: |
     /* ── Global ─────────────────────────────────────────── */
     section {
       font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
       font-size: 27px;
       padding: 50px 64px 64px;
       background: #ffffff;
       color: #1a1a2e;
     }
     /* thin accent bar across the top of every regular slide */
     section::before {
       content: '';
       position: absolute;
       top: 0; left: 0; right: 0;
       height: 6px;
       background: linear-gradient(90deg, #1e3a6e 60%, #2e86de 100%);
     }
     /* ── Title slide ─────────────────────────────────────── */
     section.title {
       background: linear-gradient(150deg, #16213e 0%, #1e3a6e 55%, #2e86de 100%);
       color: #ffffff;
       justify-content: flex-end;
       padding-bottom: 80px;
     }
     section.title::before { display: none; }
     section.title h1 {
       font-size: 60px;
       font-weight: 800;
       color: #ffffff;
       border-bottom: 3px solid #5bb8f5;
       padding-bottom: 16px;
       margin-bottom: 16px;
     }
     section.title p {
       color: #a8d4f5;
       font-size: 26px;
       margin: 4px 0;
     }
     /* ── Slide headings ──────────────────────────────────── */
     h2 {
       color: #1e3a6e;
       font-size: 36px;
       border-bottom: 3px solid #2e86de;
       padding-bottom: 8px;
       margin-bottom: 22px;
     }
     /* ── Tables ──────────────────────────────────────────── */
     table {
       border-collapse: collapse;
       width: 100%;
       font-size: 23px;
       margin-top: 4px;
     }
     th {
       background: #1e3a6e;
       color: #ffffff;
       padding: 9px 13px;
       text-align: left;
       font-weight: 600;
     }
     td {
       padding: 7px 13px;
       border-bottom: 1px solid #ccd9ea;
     }
     tr:nth-child(even) td { background: #f0f5fb; }
     tr:last-child td { border-bottom: 2px solid #1e3a6e; }
     /* ── Bullets ─────────────────────────────────────────── */
     ul { padding-left: 22px; }
     li { margin-bottom: 7px; line-height: 1.55; }
     /* ── Page numbers ────────────────────────────────────── */
     section::after {
       color: #8aabb5;
       font-size: 14px;
     }
   ---

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