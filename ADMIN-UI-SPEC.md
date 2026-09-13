# ADMIN-UI-SPEC – Hub & Circles management tool (Streamlit)

Binding specification for the Streamlit pages in `manager/ui/`, extracted from Claude Design
frames 1d (all pages), 3f (ITRS, segment editor, coverage) and 3g (maintenance status) on
12 Sep 2026. `../ARKKITEHTUURI.md` §4.1 lists the responsibilities; this file describes what each
page shows and how forms behave. The tool stays within stock Streamlit components: sidebar
navigation, form widgets, dataframes, `st.metric`, `st.info/warning/error`, `streamlit-folium`
maps. Font is Streamlit's default (Source Sans 3). No custom CSS beyond what Streamlit exposes.

Identifiers are English (P10). The tool's own UI language is Finnish (single language, maintainer
tool); strings live in one module `manager/ui/texts.py` so they can be swapped later.

## 1. Shell (1280 × 900 reference)

- Sidebar 230 wide: title "Napa ja piirit" + "hallintatyökalu"; pages in this order: **Reitit**
  (routes), **Tasot** (layers), **Palvelut** (services), **Ilmoitukset** (reports), **Teemat**
  (themes), **Build ja julkaisu** (build & publish). Multipage app via `pages/`.
- Sidebar footer: source data status – repo name, "N muutosta commitoimatta" (git status of
  `DATA_DIR`), "Viimeisin julkaisu <date time>"; on the Routes page also the current route and its
  themes.
- Every page: `st.title`, then content in `st.columns` as described. Long-running actions
  (fetch, build, publish) run with `st.status` and show the CLI equivalent (`python -m manager …`).

## 2. Reitit (routes)

### 2.1 Import / edit form (left column, ~460 px)

- Dropzone: "Raahaa GPX-jälki ja kuvat tähän" + hint "Alkuperäiset kuvat suoraan kamerasta, jotta
  EXIF-sijainnit säilyvät" (`st.file_uploader`, multiple).
- Language tabs "Suomi" / "English" – the English tab shows a count of missing translations
  ("2 puuttuu"). Fields per language: Nimi, Kuvaus.
- Teemat (multiselect of theme ids, shown by name), Kaudet (multiselect), Vaativuus (selectbox
  easy/moderate/demanding shown as helppo/keskivaativa/vaativa).
- Summary line "ITRS ja vaativin kohta: 2 sininen · vaativin kohta km 19,4 — Muokkaa" linking to
  the sections below.
- Ylläpito (selectbox: kunnan ylläpitämä / ei kunnan ylläpitämä / ei tietoa), Lipas-tunnus (text,
  disabled grey "– ei kytkentää" when empty).
- Info box when a legacy value was normalised: "Vanha arvo keskivaikea normalisoitiin muotoon
  keskivaativa tuonnissa."
- Buttons: primary "Tallenna reitti", secondary "Hae maastokartta reittikäytävältä".

### 2.2 Preview (right column)

- `st.metric` row: Pituus "32,4 km", Nousu "410 m", Kuvia "7".
- Map (streamlit-folium): track line, photo markers at EXIF positions.
- Warning when photos lack EXIF: "2 kuvassa ei ole EXIF-sijaintia. Ne näkyvät galleriassa mutta
  eivät kartalla."

### 2.3 Routes table (below)

Columns: nimi, teemat, käännös (languages present), ylläpito ("kunta" / "ei kunnan · 3 syytä").
Row click loads the route into the form.

### 2.4 ITRS assessment (section "ITRS-arvio", frame 3f)

Two rows of `st.columns`:
- Tekninen vaikeus, Kestävyys: selectbox whose options render as "<n> <name>" with a 14×14 color
  swatch (use option labels "1 vihreä" … "5 oranssi" plus "–"; color shown in a caption below since
  Streamlit selectbox cannot color options).
- Altistus, Erämaisuus: `st.number_input` min 1, step 1 (integers only). Vaativuus selectbox.
- Arvioija (default from `.env` `ASSESSOR_NAME` or last used), Arvioitu (date, default today).
- Warning box (amber): "Asteikkoa ei ole lukittu: altistus ja erämaisuus validoidaan vain
  positiivisina kokonaislukuina, kunnes ITRS-oppaan tasot on tarkistettu."

### 2.5 Hardest section ("Vaativin kohta")

- Thumbnail grid of the route's photos (84×62 each); selected has a 2 px `#2F6F7E` border.
- Km (number, prefilled from EXIF projection, editable) + Kuvaus (fi) / (en) text inputs.
- Caption: "Km laskettu kuvan EXIF-sijainnista projisoimalla. Voit korjata arvon."

### 2.6 Segment editor ("Segmenttieditori")

- Header with coverage: "kattavuus 88 % · 2,6 km ilman tietoa".
- Elevation profile (SVG or `st.pyplot`-free: use `st.altair_chart`/`st.vega_lite_chart` or a
  static SVG via `st.markdown`) with dashed vertical lines at segment boundaries, a surface lane
  below (18 h, colors from UI-SPEC §1.4) and a km axis 0 / 5 / 10 / 15 / 21,3.
- Table (`st.data_editor`): columns alku, loppu, pinta, liikenne, tekninen, plus an action column.
  Gaps are rendered as an amber row "aukko · 2,6 km · tuntematon · täytä tai jätä aukoksi" with
  "lisää".
- Buttons: primary "Tallenna segmentit", secondary "Aseta raja klikkaamalla karttaa" – map click
  (streamlit-folium `last_clicked`) is projected onto the track and converted to km, filling the
  boundary field of the active row. Caption: "Klikkaus projisoidaan reittiviivalle ja muutetaan
  kilometriksi. Reittiviivaa ei piirretä työkalussa (AP4)."
- Validation shown inline before save: ordering, overlap, range 0…length+0.05.

### 2.7 Maintenance status ("Ylläpito", frame 3g)

- Ylläpito selectbox (see 2.1). When "ei kunnan ylläpitämä":
  - Lipas-tunnus disabled, shows "– ei kytkentää".
  - Checkbox list "Syyt · vähintään yksi": yksityistie, ei lupaa / ei reittimerkintöjä /
    ei kunnossapitoa / maastoliikennelaki / kausiluonteinen (ids per ARKKITEHTUURI §5.7).
  - Tarkennus (fi) / (en) text inputs → `maintenance_note`.
  - Error box if saved with no reason: "Validointi: ylläpito on non_municipal, mutta syytä ei ole
    valittu → virhe. Build pysähtyy, koska merkintä ilman perustelua on harhaanjohtava."
- When "kunnan ylläpitämä": Lipas-tunnus editable; reasons hidden.
- Lipas suggestion (ARKKITEHTUURI §7.13): after a track is imported the tool compares it with the
  Lipas snapshot and, on a match, shows an info box "Lipas ehdottaa: 613791 · Arctic by Cycle:
  Santa's Western Gravel · 92 % jäljestä 30 m sisällä" with buttons "Hyväksy kytkentä" (sets
  maintainer = municipal and lipas_id) and "Ohita". No automatic write. If the Lipas snapshot is
  missing or older than 90 days, a caption suggests running "Hae Lipas" (Palvelut page).

## 3. Tasot (layers)

- Table: taso, paikka, muoto, koko ("433 tiiltä", "18,4 MB", "84 kB"), teemat, oletus (päällä/pois).
- Edit panel "Muokkaa: <name>": Lähde (selectbox of source methods), Julkaisumuoto (xyz/pmtiles),
  file info caption "luke/bilberry_2026.tif · 20 m/px · EPSG:3067 · maxzoom 12".
- "Luokat, värit ja selite": editable table value / color / fi label / en label.
- Buttons: "Tallenna taso", "Tiilitä uudelleen".
- "Näkyvyys": checkboxes per theme (by name) + "Lisäksi reitillä:" multiselect of routes.
- Preview map and a limits note: "Mahtuu Cloudflare Pagesin 25 MiB:n tiedostorajaan." (or the
  failing limit in red).

## 4. Palvelut (services)

- Buttons: "Hae OSM:stä", "Hae Visit Finlandista"; caption "Edellinen tilannekuva <date time>".
- `st.metric` row: Uusia "+12", Poistuneita "−3", Muuttuneita "7", Yhteensä "318".
- "Muutokset edelliseen tilannekuvaan" table: muutos (uusi/poistui/muuttui/ennallaan), nimi,
  kategoria, id, toiminto (tarkista / piilota / vertaa / avaa).
- Warning when a manual override targets a removed point: "Käsin tehty korjaus kohteeseen
  osm:node/442 jäisi toimimattomaksi, jos piste poistetaan. Tarkista ennen buildia."
- Primary "Hyväksy tilannekuva" writes the snapshot into `DATA_DIR/services/`.
- Third button "Hae Lipas" fetches the municipal route register (WFS, ARKKITEHTUURI §7.13) into
  `DATA_DIR/lipas/routes.geojson`; shows count per type ("pyöräilyreitit 12, maastopyöräilyreitit
  4, …") and a map preview before "Hyväksy Lipas-tilannekuva".
- Map with change legend (uusi / poistui / muuttui / ennallaan) and "Lisää piste klikkaamalla
  karttaa" → manual point form (category, name fi/en, url, opening hours).

## 5. Ilmoitukset (reports)

- Button "Hae GitHubista"; caption "4 avointa ilmoitusta · label trail-issue · haettu <time>".
- List of issues; the selected one expands: "#42 Kaatunut puu", "@user · date · <route>", body
  quoted as plain text (never published), "66.5031, 25.7294 · kuva liitteenä · julkaisulupa
  annettu".
- Form: "Julkaistava kuvaus (kirjoitetaan itse)" fi/en, Vakavuus (selectbox), Voimassa asti (date).
- Buttons: primary "Hyväksy ongelmakohdaksi" (writes to `services/issues.geojson`, comments and
  labels the issue), secondary "Hylkää ja sulje".
- Map with open reports; image preview only if permission was granted (caption: "Ilmoittajan kuva.
  Tuodaan mediaputken läpi vain, jos julkaisulupa on annettu lomakkeella.").

## 6. Teemat (themes)

- Intro caption: "Järjestys määrää myös piirien järjestyksen tunnuksessa, sisältä ulos.
  Esitys-osio ratkaisee, mitkä tiedot nousevat reittilistaan ja reittikortin kärkeen."
- One expander per theme, ordered by `order`, header "<Name> · järjestys N": color inputs
  (primary, highlight) with computed contrast against white ("Kontrasti valkoista tekstiä vasten
  6,1:1", red if < 4.5), Pohjakartta selectbox (optional), Oletustasot multiselect, and the
  presentation lists as multiselects restricted to the fixed identifiers (ARKKITEHTUURI §5.7):
  avainluvut, nauha (max 3 besides elevation), nosta kuva, suodattimet, palvelut ensin.
- "Tunnus ja uusi teema": live preview of the `HubLogo` rings from the current themes; caption
  "Uusi teema on datamuutos: väri, järjestys ja esitys-osio. Tunnukseen tulee automaattisesti uusi
  piiri, eikä frontendiin tarvita koodimuutosta."

### 6.1 Projektiasetukset (expander at the bottom of Teemat)

- ITRS-asteikot: two `st.number_input`s "Altistus, tasoja" and "Erämaisuus, tasoja" with a
  "ei lukittu" checkbox each; unchecked → `project.itrs_scales.<dim> = null`. Caption: "Tarkista
  tasojen määrä ITRS-oppaasta (itrs.bike) ja Suomen Ladun oppaasta. Kun asteikko on lukittu,
  validointi vaatii arvon 1…max ja frontend näyttää 'n / max'."
- Also here: oletusteema, oletuskieli, lähipalvelut (m), palaute (github_repo, issue_form).

## 7. Build ja julkaisu (build & publish)

The page is a three-step workflow, top to bottom, each step in its own `st.container(border=True)`
with a numbered header and one sentence saying what happens and where. Every step names its CLI
equivalent in a caption. Steps that are not ready yet are shown but their buttons are disabled
with the reason in a caption (never hidden).

**Intro caption** (under the title): "Muutokset syntyvät Reitit- ja Teemat-sivuilla lähdedataan
(`hubandcircles-data`). Build tekee niistä julkaisudatan, esikatselu näyttää sen sivuston kanssa,
ja julkaisu vie paketin sivustolle ja lähdedatan GitHubiin."

**1 · Build** – "Lähdedata → julkaisudata (`dist/`). Tarkistaa skeeman, linkit, viittaukset,
käännökset ja avainvuodot; virhe pysäyttää." Primary button "Aja build" with `st.status`. After
success: caption "Valmistui <HH:MM:SS> · N s", `st.metric` row Reittejä / Ensikäynti / Varoituksia,
and the "Tarkistukset" list: ✓ per passed check, "! <check> · N varoitusta" with a "Näytä"
expander listing the messages. On `BuildError`: the error list. Only checks that exist are listed.
Sidebar/state: the time of the last successful build is kept in `.state.json` and shown as caption
"Edellinen build <time>" when the button has not been pressed in this session.

**2 · Esikatselu** – "Näyttää julkaisudatan yhdessä frontend-buildin kanssa paikallisesti; tämä on
täsmälleen se paketti, joka julkaistaan." Button "Käynnistä esikatselu" (disabled with caption
"Aja build ensin" when no build has succeeded since the data changed – compare `dist/`'s
`catalog.json` mtime with the newest mtime under `DATA_DIR`), starts `python -m manager preview`
in the background, waits until it answers, then shows `st.link_button("Avaa esikatselu",
url)` (new tab) and "Pysäytä esikatselu". If it does not answer: `st.error` + the log tail.
Frontend missing → warning "Buildaa frontend: cd hubandcircles-ui && npm run build" and the
button disabled. Caption: "Esikatselu jää käyntiin kunnes pysäytät sen tai suljet Streamlitin."

**3 · Julkaise** – "Vie paketin (frontend + `data/`) julkaisukohteisiin ja tallentaa lähdedatan
GitHubiin, jotta sivusto ja data ovat samassa tilassa." Contents:
- Targets as checkboxes from `publish.json` (label `<id> · <type> · <repo|project|path>`) and the
  caption "Frontend: <path>".
- "Lähdedata: <repo> · haara <branch> · N muutosta commitoimatta · M pushaamatta"; when N+M > 0 a
  checkbox "Tallenna lähdedata GitHubiin (commit + push)" checked by default and a text input
  "Commit-viesti" (default "Update route data"); when 0 the caption "Lähdedata on jo GitHubissa".
- Primary button "Julkaise" (disabled with caption "Aja build ensin" under the same rule as step
  2; disabled with "Ei julkaisukohteita" when none is selected). Runs inside one `st.status` with
  a line per sub-step: "Paketti koottu: N tiedostoa, X MiB", "pages: pushed to <repo> gh-pages",
  "Lähdedata: <commit hash> pushattu" (or "ei muutoksia"). Order: publish the site first, then
  commit and push the data – a failed site publish must not leave the data repo ahead of the
  site. On success: `st.success` "Julkaistu <time>" with `st.link_button` to the site URL when the
  target is `github-pages` (`https://<owner>.github.io/<repo>/`), caption "GitHub Pages päivittyy
  noin minuutissa." On error: `st.error` with the message; the sub-steps already done stay listed.
- Caption with both CLI equivalents: `python -m manager publish --target …` and
  `git -C <DATA_DIR> add -A && git commit -m "…" && git push`.

Not on this page yet (V5): coverage table, target-limit percentages, host check.

## 8. Rules

- Pages call `manager.*` functions only; no logic, file writes or network in `manager/ui/`.
- Every fetch shows the diff against the previous snapshot before it is accepted.
- Frequent tasks are one button; each button names its CLI equivalent in a caption.
- Validation messages reuse `manager.validate` findings verbatim; the UI never re-implements a check.
