# Thumbnail Image Prompt Patterns

How to turn a thumbnail brief into a prompt for an image model (Nano Banana / Gemini,
GPT-4o image, Doubao, etc.). Used by `sub-skills/thumbnail.md` when image generation is available.

> Patterns distilled from the **Awesome Prompt Gallery** curated by 松果先森
> ([opennana.com/awesome-prompt-gallery](https://opennana.com/awesome-prompt-gallery/) ·
> [X @songguoxiansen](https://x.com/songguoxiansen)), cases 301-400, which collect prompts by many
> original authors. Templates below are rewritten and adapted for 16:9 YouTube thumbnails;
> case numbers point back to the source entries.

## Two Prompt Shapes

| Shape | Use when | Notes |
|-------|----------|-------|
| **Prose** (1-6 sentences) | Simple concept, one subject, one mood | Order: subject → action/pose → setting → lighting → camera → style → format |
| **Structured spec** (JSON-like keys) | Many constraints that must all hold (face, outfit, props, light, negatives) | Models follow keyed blocks more reliably than long prose; keep keys plain English |

Structured spec skeleton (cases 364, 330, 393 use this shape):

```json
{
  "format": "16:9 YouTube thumbnail, 1280x720 minimum",
  "subject": {"identity": "...", "expression": "...", "pose": "...", "wardrobe": "..."},
  "scene": {"setting": "...", "background": "...", "props": "..."},
  "camera": {"framing": "...", "angle": "...", "lens": "85mm portrait, shallow depth of field"},
  "lighting": {"key": "...", "fill": "...", "rim": "...", "mood": "..."},
  "color_grade": {"palette": "...", "contrast": "high", "saturation": "vibrant"},
  "composition": "subject in right third, clean negative space on the left for title text",
  "negative": ["extra fingers", "warped hands", "plastic skin", "random text", "watermark"]
}
```

## Building Blocks

**Keep the creator's real face** (when a reference photo is attached — cases 375, 377, 379, 384):
"Use the attached photo as the face reference; keep facial features, proportions and skin tone
identical. Do not beautify, slim or restyle the face." State it once at the start and once at the end.

**Camera language that models respect:**
- `85mm portrait lens, f/1.8, shallow depth of field` → face-led thumbnails, blurred background
- `slightly low angle` → authority/power; `slightly high angle, selfie perspective` → casual, relatable
- `ultra-wide fisheye, extreme distortion, camera very close` → comedic/energetic (cases 315, 394)
- `100mm macro, f/2.8` → tiny-subject or detail shots (case 383)
- `extreme close-up on eyes and mouth` → emotion-first thumbnails

**Lighting recipes:**

| Recipe | Prompt wording | Fits |
|--------|----------------|------|
| Clean studio | "large softbox key 45° front-left, soft fill right, subtle rim light, seamless backdrop" | Tutorials, reviews |
| Hard drama | "single hard side light, deep shadows, high-contrast chiaroscuro" | Commentary, essays, true crime |
| Pop high-key | "bright even ring-flash lighting, no shadows, saturated colours" | Entertainment, challenges |
| Split colour | "cool blue background light, warm orange spotlight on face" (case 366) | Tech, gaming, cinematic |
| Direct flash | "on-camera flash, harsh highlights, slight grain, candid snapshot" (case 340) | Vlogs, IRL, nostalgia |

**Negative block** (append to every prompt): extra or fused fingers, warped hands, deformed limbs,
plastic/waxy skin, oversharpened halos, random or misspelled text, watermarks, cluttered background.

## Pattern Library → Thumbnail Use

| Pattern (source cases) | Template (fill the brackets) | Best for |
|------------------------|------------------------------|----------|
| Giant product in the real world (321) | "Ultra-realistic CGI shot of a giant [PRODUCT] integrated into a [ENVIRONMENT that matches its identity], natural shadows and reflections, cinematic composition" | Reviews, unboxings |
| Product skinned in a texture (322) | "Studio photo of [PRODUCT] fully covered in realistic [TEXTURE: fur/scales/ice/moss], shape and design still recognisable, soft neutral background" | Tech/product hooks |
| Sliced object + cartoon blast (311) | "[OBJECT] cut cleanly in half, halves floating apart, a stylised cartoon explosion of glowing smoke between them; outside stays photoreal" | "What's inside", teardowns |
| Cartoon doodles on a real object (320, 380) | "Real [OBJECT] photographed in a clean studio, hand-drawn black doodle face and arms on it showing [EMOTION], pastel [COLOUR] background" | Light-hearted explainers |
| Creator + oversized prop (398) | "Full-body studio shot of [CREATOR] sitting on a giant [OBJECT], object grounded with real contact shadows, seamless [COLOUR] wall and floor" | Lifestyle, finance ("giant coin"), food |
| Creator beside a big creature (346, 347, 374) | "[CREATOR] standing confidently beside a [ORIGINAL CREATURE] taller than them, outfit colours echo the creature, glossy reflective floor, colour-gradient backdrop" | Gaming, storytelling |
| Tiny figure between fingers (383) | "Hyper-real macro photo of a 10 cm [SUBJECT] held between a real thumb and finger, accurate contact shadows, grey gradient background" | "Small but mighty", miniatures |
| 3D caricature of the creator (302, 313) | "Stylised 3D caricature of [CREATOR] from the reference photo, oversized expressive head, small body, [POSE], Pixar-style render, bold solid background" | Channel branding, series art |
| Vinyl figure in a box (315, 382) | "Chibi vinyl collectible of [CREATOR] standing in a window-box package with [CHANNEL NAME] on the box, 3/4 product shot" | Milestone/merch videos |
| Multi-panel composite (309, 384) | "Three stacked panels: [CLOSE-UP], [FULL SHOT], [DETAIL SHOT], consistent face and outfit, same grade" | Before/after, comparisons |
| Blueprint drawing (304) | "Technical drawing of [OBJECT] on white paper, pencil linework, red-marker dimensions and callouts for [PARTS]" | Engineering, how-it-works |
| Text-as-shape (307, 316) | "Typographic illustration where the word '[WORD]' forms the silhouette of a [OBJECT], bold playful letters, solid background" | Title cards, one-word hooks |
| Paper-cut / retro comic (305, 306) | "Layered paper-cut illustration of [SUBJECT] in soft [COLOUR 1] and [COLOUR 2]" / "vintage comic panel, bold outlines, halftone dots, motion streaks" | Kids, history, storytelling |
| Surreal metaphor (338) | "A massive [PHENOMENON] tearing through [SETTING], revealing [OUTCOME] — visual metaphor for [IDEA]" | AI, future, big-idea essays |
| Many copies of one subject (301) | "Portrait of [CREATOR] centred, surrounded by dozens of life-size stone busts of themselves, warm museum light" | "100 versions of me", challenges |
| Glass profile card (395, 396) | "Hand holding a translucent acrylic card showing a social profile with [DETAILS], neon edge glow, dark blurred background" | Social-media growth topics |
| Dramatic B&W portrait (357, 365, 373) | "Black-and-white studio portrait, single hard side light, deep shadows, film grain, intense gaze at camera" | Serious commentary, documentaries |

## Adapting Gallery Prompts to Thumbnails

1. **Force 16:9.** Most gallery prompts are 3:4 or 9:16 portraits. Say "16:9 horizontal" and move
   the subject to a third so the composition still works.
2. **Reserve text space.** Add "clean negative space on the [left/right] for title text". Image
   models still misspell words — ask for at most 1-3 large words, or add the text afterwards in an
   editor. Never let the image repeat the video title (see the Information Split Rule in
   `references/thumbnail-ctr-guide.md`).
3. **Push contrast and scale.** Gallery prompts are tuned for full-screen viewing; thumbnails are seen
   at ~120 px wide on mobile. Ask for one focal point, a larger face, simpler background and higher
   saturation than the source prompt.
4. **Specify the emotion precisely.** "Genuine shocked expression, wide eyes, open mouth" beats
   "surprised". Match it to the hook (curiosity, shock, delight, concern).
5. **Generate the A/B set by changing one variable** per variant (expression, background colour,
   composition or prop), so the test result is attributable.
6. **Check at small size** before delivering: downscale to 168×94 and confirm the focal point and any
   text still read.

## What Not to Borrow

- **Real people and celebrities** (case 355 uses named actors) — likeness and impersonation risk,
  and misleading-thumbnail strikes. Use only the creator's own face or consenting collaborators.
- **Trademarked characters and logos** (Sonic, Mario, Pokémon, Marvel, Funko/Youtooz box branding in
  cases 315, 346-348, 355, 382, 394) — replace with original mascots and the channel's own name.
  Brand logos are fine only for products the video genuinely reviews.
- **Sexualised or suggestive framing.** Much of the gallery is glamour/boudoir portraiture
  (lingerie, undressing, bed shots, "alluring" poses). These are suppression triggers and age-restriction
  risks on YouTube (see Suppression Triggers in `references/thumbnail-ctr-guide.md`) and add nothing
  to CTR for most niches. Keep wardrobe and poses appropriate for a general audience.
- **Misleading scenes** that don't happen in the video — clickbait penalties outweigh a CTR spike.
- **Age ambiguity.** Always describe adult subjects as adults; never generate minors in fashion,
  glamour or romantic contexts.
