# Artiou artwork/entity page briefs: Mona Lisa, Venus de Milo, Monet Water Lilies

Purpose: create the first three evergreen artwork/entity pages for Artiou. These are page-production briefs, not final published copy. The tone target is art beginners visiting a museum with a phone in hand: clear, warm, practical, and curiosity-led rather than academic.

Global page pattern for all three pages:

1. Hero: entity name, aliases, one-sentence promise, museum/location, primary CTA.
2. Quick facts: artist, date/period, medium, movement/style, museum room/location, expected viewing time.
3. 60-second explanation for beginners.
4. Why it matters.
5. What to look for in person.
6. Common misconceptions.
7. Related works, route links, and internal-link cluster.
8. FAQ.
9. Schema blocks: `VisualArtwork`, `Person`, `Museum`, `FAQPage`.
10. App CTA: “Use Artiou as your pocket curator in the museum.”

Recommended URL pattern:

- `/en/artworks/mona-lisa/`
- `/en/artworks/venus-de-milo/`
- `/en/artworks/monet-water-lilies/`

---

## 1. Mona Lisa guide

### Entity name / aliases / original language name

- Primary name: Mona Lisa
- Original/Italian name: La Gioconda
- French name: La Joconde
- Other common aliases: Portrait of Lisa Gherardini, Portrait of Mona Lisa
- Search variants to support naturally: Mona Lisa Louvre guide, La Joconde explained, why is Mona Lisa famous, Mona Lisa meaning

### Museum/location

- Museum: Musée du Louvre, Paris
- Department: Paintings
- Typical location: Salle des États, Denon wing
- Visitor context: usually crowded, often viewed from several meters away behind protective glass

### Artist / period / movement

- Artist: Leonardo da Vinci
- Date: c. 1503–1519
- Period: High Renaissance
- Movement/style: Italian Renaissance portraiture; sfumato technique
- Medium: Oil on poplar panel

### 60-second explanation for beginners

The Mona Lisa is famous not because it is large or dramatic, but because it feels unusually alive. Leonardo softened the transitions around the mouth, eyes, and face using a technique called sfumato, so the expression seems to shift as you look. The portrait also combines a very real person with an almost dreamlike landscape, making the painting feel both intimate and mysterious. In the Louvre, the challenge is to look beyond the crowd and notice how quietly controlled the image is: the folded hands, the turn of the body, the soft shadow at the mouth, and the landscape that seems to recede into another world.

### Why it matters

- It is one of the clearest examples of Leonardo’s attempt to paint not just a likeness, but the sensation of a living mind.
- It changed expectations for portraiture: the sitter is not stiffly presented; she appears psychologically present.
- Its fame is also historical: royal ownership, the Louvre’s central role, the 1911 theft, mass reproduction, and modern tourism all amplified its status.
- For Artiou, it is a perfect beginner page because it teaches visitors how to look at a work they already think they know.

### What to look for in person

- The mouth: the smile is not a line; it is created through soft shadows that change with distance.
- The eyes: notice how the gaze seems stable even while the expression remains ambiguous.
- The hands: their calm placement anchors the entire composition.
- The veil and hair: subtle details are easy to miss in reproductions.
- The landscape: the horizon lines do not fully match on both sides, adding a strange dreamlike quality.
- Scale surprise: many first-time visitors expect a huge painting; the work is relatively small compared with nearby monumental canvases.

### Common misconceptions

- “It is famous only because it was stolen.” The theft helped global fame, but the painting was already admired for Leonardo’s technique and psychological subtlety.
- “The smile is a hidden code.” The mystery is less a puzzle to solve than a visual effect created through soft transitions and peripheral vision.
- “You need to stand at the front to understand it.” A little distance often makes the expression easier to perceive.
- “The painting is disappointing because it is small.” Its power is intimate; the small scale is part of how it works.

### Related works and route links

Internal link plan:

- Museum guide ↔ artwork: `/en/museums/louvre/` ↔ `/en/artworks/mona-lisa/`
- Artwork ↔ artist: `/en/artworks/mona-lisa/` ↔ `/en/artists/leonardo-da-vinci/`
- Artwork ↔ route: `/en/routes/louvre-first-visit/` and `/en/routes/louvre-renaissance-highlights/`
- Related Louvre works:
  - Leonardo da Vinci, `Virgin of the Rocks`
  - Leonardo da Vinci, `Saint John the Baptist`
  - Veronese, `The Wedding Feast at Cana` (same room context and scale contrast)
  - Jacques-Louis David, `The Coronation of Napoleon` (crowd-management route pairing)

### FAQ

**How long should I spend with the Mona Lisa?**
For a first visit, 3–5 focused minutes is enough: look at the face, hands, and landscape rather than trying to wait for a perfect crowd-free moment.

**Why is the Mona Lisa behind glass?**
It is protected because of its value, fragility, and the extremely high number of visitors.

**Is the Mona Lisa really small?**
Yes, it is much smaller than many visitors expect, especially compared with large Louvre history paintings nearby.

**Where is the Mona Lisa in the Louvre?**
It is usually displayed in the Salle des États in the Denon wing, but visitors should confirm the current room on the Louvre map before going.

**What should beginners notice first?**
Start with the smile from a short distance, then the eyes, hands, and the strange landscape behind her.

### Schema/entity markup plan

- `VisualArtwork`
  - `name`: Mona Lisa
  - `alternateName`: La Gioconda, La Joconde, Portrait of Lisa Gherardini
  - `creator`: Leonardo da Vinci
  - `artMedium`: Oil on poplar panel
  - `artform`: Painting
  - `dateCreated`: c. 1503–1519
  - `locationCreated`: Italy / France context if needed with cautious wording
  - `isPartOf`: Louvre collection
- `Person`
  - `name`: Leonardo da Vinci
  - `sameAs`: Wikidata / authoritative museum references when available
- `Museum`
  - `name`: Musée du Louvre
  - `address`: Paris, France
- `FAQPage`
  - Use the five FAQ entries above.

### App CTA

Use Artiou as your pocket curator in the Louvre: open the Mona Lisa stop, get a 60-second explanation while you are in the room, then continue to nearby Renaissance highlights without getting lost in the crowd.

---

## 2. Venus de Milo guide

### Entity name / aliases / original language name

- Primary name: Venus de Milo
- French name: Vénus de Milo
- Greek reference: Aphrodite of Milos
- Other common aliases: Aphrodite of Melos, Venus of Milo
- Search variants to support naturally: Venus de Milo Louvre guide, why does Venus de Milo have no arms, Aphrodite of Milos explained

### Museum/location

- Museum: Musée du Louvre, Paris
- Department: Greek, Etruscan, and Roman Antiquities
- Typical location: Sully wing, classical sculpture galleries
- Visitor context: a major Louvre icon with a steadier viewing experience than the Mona Lisa, but still a high-traffic stop

### Artist / period / movement

- Artist: traditionally attributed to Alexandros of Antioch, though attribution is not fully secure
- Date: c. 150–125 BCE
- Period: Hellenistic Greek art
- Movement/style: Hellenistic sculpture with classical idealizing features
- Medium: Marble

### 60-second explanation for beginners

The Venus de Milo is a marble statue of Aphrodite, the Greek goddess of love, known today for the missing arms that make her instantly recognizable. What matters is not only what is missing, but how the body is composed. The figure twists gently: the hips shift, the torso turns, and the drapery drops around the legs, creating a balance between calm beauty and movement. The statue feels ancient and idealized, but also physical and present. Instead of treating the missing arms as a mystery to solve immediately, start by looking at the rhythm of the body from the feet upward.

### Why it matters

- It is one of the Louvre’s defining ancient sculpture icons.
- It gives beginners an accessible entry into Hellenistic sculpture: ideal beauty, movement, theatrical presence, and fragmentary survival.
- The missing arms shaped the statue’s modern fame, but the sculpture’s quality lies in the body’s balance and the relationship between nude torso and draped lower body.
- It is a strong bridge page between museum route planning and foundational art-history concepts.

### What to look for in person

- The contrapposto: weight rests more on one leg, making the body feel alive rather than rigid.
- The twist: shoulders, torso, and hips do not face exactly the same direction.
- The drapery: the cloth both reveals and conceals the body, creating visual tension.
- The back view: if circulation allows, look from the side or behind to understand the three-dimensional composition.
- The surface: notice how marble can suggest soft skin and heavy fabric at the same time.
- The missing arms: use them as a reminder that ancient art often reaches us as fragments, not pristine originals.

### Common misconceptions

- “The missing arms make it valuable.” The missing arms make it memorable, but the statue is admired for composition, carving, and historical importance.
- “We know exactly what pose she had.” Several reconstructions have been proposed, but the original arm position is uncertain.
- “It is a Roman copy like many ancient statues.” The Venus de Milo is generally treated as an original Hellenistic Greek work or at least more directly connected to Greek production than many later Roman copies.
- “Ancient statues were always pure white.” Many ancient sculptures were originally painted or displayed in more colorful contexts, even if the marble appears white today.

### Related works and route links

Internal link plan:

- Museum guide ↔ artwork: `/en/museums/louvre/` ↔ `/en/artworks/venus-de-milo/`
- Artwork ↔ artist/entity: `/en/artworks/venus-de-milo/` ↔ `/en/entities/aphrodite/` and `/en/artists/alexandros-of-antioch/` if artist pages are supported
- Artwork ↔ route: `/en/routes/louvre-first-visit/`, `/en/routes/louvre-ancient-icons/`
- Related Louvre works:
  - `Winged Victory of Samothrace`
  - `Diana of Versailles`
  - `Sleeping Hermaphroditus`
  - Greek and Roman sculpture gallery overview
- Cross-page concept links:
  - `What is contrapposto?`
  - `Greek gods in the Louvre`

### FAQ

**Why does the Venus de Milo have no arms?**
The arms were already missing when the statue entered modern history. Their exact original position remains uncertain.

**Is Venus de Milo Greek or Roman?**
It is generally identified as a Hellenistic Greek sculpture from the island of Milos.

**Who made the Venus de Milo?**
It has often been linked to Alexandros of Antioch, but the attribution is not fully certain.

**What is the statue supposed to represent?**
It is usually understood as Aphrodite, the Greek goddess of love, known as Venus in Roman mythology.

**Is it worth seeing if I only have two hours in the Louvre?**
Yes. It is one of the museum’s key icons and pairs well with the Mona Lisa and Winged Victory on a first-visit route.

### Schema/entity markup plan

- `VisualArtwork`
  - `name`: Venus de Milo
  - `alternateName`: Vénus de Milo, Aphrodite of Milos, Aphrodite of Melos
  - `creator`: Alexandros of Antioch, with cautious attribution note if schema allows
  - `artMedium`: Marble
  - `artform`: Sculpture
  - `dateCreated`: c. 150–125 BCE
  - `contentLocation`: Milos / Melos, Greece
  - `isPartOf`: Louvre collection
- `Person`
  - `name`: Alexandros of Antioch
  - Include only if the page copy explains the attribution uncertainty.
- `Museum`
  - `name`: Musée du Louvre
- `FAQPage`
  - Use the five FAQ entries above.

### App CTA

Use Artiou as your pocket curator in the Louvre: stand in front of the Venus de Milo, learn how to read the pose and drapery in one minute, then follow the route to the Winged Victory and other ancient icons.

---

## 3. Monet Water Lilies guide

### Entity name / aliases / original language name

- Primary name: Monet Water Lilies
- French name: Les Nymphéas
- More precise entity: Monet’s Water Lilies cycle at the Musée de l’Orangerie
- Related aliases: Nymphéas, Water Lilies rooms, Monet at the Orangerie
- Search variants to support naturally: Monet Water Lilies Paris guide, Orangerie Water Lilies explained, Les Nymphéas guide, why are Monet Water Lilies important

### Museum/location

- Museum: Musée de l’Orangerie, Paris
- Location: two oval rooms designed for the large Water Lilies ensembles
- Visitor context: immersive, slow-looking experience; best understood by moving around the rooms rather than treating each panel as a separate framed picture

### Artist / period / movement

- Artist: Claude Monet
- Date: mainly 1914–1926 for the Grandes Décorations; subject developed over decades at Giverny
- Period: late Impressionism / early modernism context
- Movement/style: Impressionism moving toward abstraction and immersive installation
- Medium: Oil on canvas, large-scale panoramic panels

### 60-second explanation for beginners

Monet’s Water Lilies at the Orangerie are not just paintings of a pond; they are an environment. Monet enlarged the view until the horizon disappears, leaving water, reflections, clouds, flowers, and light. Instead of telling a story, the rooms invite you to slow down and notice how vision changes from moment to moment. Up close, the brushstrokes can look loose and almost abstract. From farther away, they become water, sky, and floating lilies. The experience is less about finding a single “main subject” and more about letting your eyes adjust to color, rhythm, and atmosphere.

### Why it matters

- The Orangerie installation is one of the most important immersive painting environments in Paris.
- It shows Monet late in life pushing Impressionism beyond outdoor observation toward all-over fields of color and near-abstraction.
- It is beginner-friendly because visitors can feel the effect before knowing the art history.
- It links naturally to Giverny, Impressionism, Orsay, and modern abstract painting.
- For Artiou, it supports a different visit mode: slow looking, quiet rooms, and emotional decompression after busier museums.

### What to look for in person

- No horizon: notice how the usual separation between sky, land, and water disappears.
- Reflections: clouds and trees often appear as reflections rather than direct views.
- Brushwork: step close to see strokes and color patches, then step back to let them reorganize into an image.
- Room design: the oval rooms shape the experience; the paintings surround rather than simply face you.
- Light changes: different panels feel like different times of day or weather.
- Edges and continuity: look at how the panels create rhythm around the room.

### Common misconceptions

- “They are just pretty flower paintings.” The Water Lilies are also experiments in perception, scale, and the boundary between representation and abstraction.
- “Impressionism is always small outdoor sketches.” These works are monumental, carefully installed, and the result of long-term studio work.
- “You should look for one best panel.” The installation matters as a whole; the room-to-room experience is the artwork’s core.
- “You need to understand modern art first.” Beginners can start with the simplest question: what changes when you move closer or farther away?

### Related works and route links

Internal link plan:

- Museum guide ↔ artwork: `/en/museums/orangerie/` ↔ `/en/artworks/monet-water-lilies/`
- Artwork ↔ artist: `/en/artworks/monet-water-lilies/` ↔ `/en/artists/claude-monet/`
- Artwork ↔ route: `/en/routes/orangerie-first-visit/`, `/en/routes/impressionism-in-paris/`, `/en/routes/orsay-orangerie-half-day/`
- Related works and places:
  - Monet works at Musée d’Orsay
  - Monet’s garden at Giverny
  - Renoir / Cézanne / Matisse works in the Jean Walter and Paul Guillaume collection at the Orangerie
  - Concept page: `What is Impressionism?`
  - Concept page: `How to look at abstract-looking painting`

### FAQ

**Where are Monet’s Water Lilies in Paris?**
The most immersive Water Lilies rooms are at the Musée de l’Orangerie, near the Tuileries Garden.

**How long should I spend in the Water Lilies rooms?**
Plan at least 15–25 minutes if you can. The paintings reward slow looking and repeated movement around the rooms.

**Are the Orangerie Water Lilies the same as the ones at Giverny?**
Giverny is Monet’s garden and studio context; the Orangerie contains the large Paris installation inspired by that garden and pond.

**Why do the paintings look abstract up close?**
Monet used loose brushwork and color relationships that become more image-like when seen from a distance.

**Is the Orangerie good for a first museum visit in Paris?**
Yes. It is smaller than the Louvre and offers a calm, focused experience that beginners often find accessible.

### Schema/entity markup plan

- `VisualArtwork`
  - `name`: Monet Water Lilies
  - `alternateName`: Les Nymphéas, Water Lilies, Grandes Décorations
  - `creator`: Claude Monet
  - `artMedium`: Oil on canvas
  - `artform`: Painting / installation-like cycle
  - `dateCreated`: mainly 1914–1926
  - `isPartOf`: Musée de l’Orangerie collection
- `Person`
  - `name`: Claude Monet
  - `sameAs`: authoritative artist references when available
- `Museum`
  - `name`: Musée de l’Orangerie
  - `address`: Paris, France
- `FAQPage`
  - Use the five FAQ entries above.

### App CTA

Use Artiou as your pocket curator at the Orangerie: enter the Water Lilies rooms, get a calm one-minute guide to what you are seeing, then follow a slow-looking route through Monet and the rest of the collection.

---

## Production notes for converting briefs into pages

- Keep paragraphs short; visitors may read while standing in a crowded room.
- Use “look first, history second”: each section should help the visitor notice something concrete.
- Add image alt text that describes the visual idea, not just the title.
- Add `sameAs` identifiers only from reliable sources during page implementation.
- Do not add pages to sitemap until they pass the future entity quality gate: HTTP 200, index/follow, self canonical, non-fallback content, real title/H1/content, FAQ, schema, and internal links.
