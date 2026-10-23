"use strict";

// The texts of the page in both languages, the same wording the tool uses elsewhere.
const TEXTS = {
  en: {
    title: "Presentation",
    intro: "Your topic or your outline becomes slides. You check the outline and download the " +
      "PowerPoint file at the end.",
    stepContent: "Content",
    stepOutline: "Outline",
    stepDone: "Done",
    heading: "What is it about?",
    tabTopic: "Topic",
    tabMarkdown: "Outline",
    topicLabel: "Topic",
    topicPlaceholder: "For example: how honeybees pollinate flowers",
    slidesLabel: "Number of slides",
    slidesHint: "Between {lo} and {hi}. Empty lets the model decide.",
    markdownLabel: "Your outline as Markdown",
    markdownPlaceholder: "# Title\n\nSubtitle\n\n## First slide\n\nWhat it shows.",
    markdownHint: "One heading per slide, the lines under it say what the slide shows. " +
      "A role in square brackets picks the layout, for example [two_columns].",
    templateLabel: "Slide master",
    templateHelp: "The slide master sets the font, colors and layout of every slide, with fixed " +
      "placeholders for title, text and images.",
    languageLabel: "Slide language",
    languageEn: "English",
    languageDe: "German",
    presenterLabel: "Name on the cover (optional)",
    presenterPlaceholder: "For example: title, first and last name",
    instructionsLabel: "Content instruction (optional)",
    instructionsPlaceholder: "For example: only chapter 2, for first-year students, with practical examples",
    styleLabel: "Instruction for the images",
    stylePlaceholder: "For example: flat vector illustration, muted blue and grey, white background",
    notesLabel: "Create speaker notes for every slide",
    notesHint: "The notes end up in PowerPoint's notes view, not on the slide itself.",
    imagesLabel: "Create images",
    modelTitle: "Model",
    modelHint: "No model is set in the environment. Enter an OpenAI-compatible endpoint and a model.",
    next: "Create outline",
    buildDirect: "Create slides",
    outlineTitle: "The outline",
    outlineLabel: "Outline",
    outlineHint: "Change the titles, move lines or delete a slide before the slides are written.",
    build: "Create slides",
    back: "Back",
    doneTitle: "The presentation is done",
    summary: "{n} slides as a PowerPoint file.",
    download: "Download PowerPoint",
    new: "New presentation",
    planning: "The outline is taking shape",
    writing: "{done} of {total} slide texts written",
    drawing: "The images are being created",
    building: "The file is being built",
    outlineFailed: "The outline could not be created.",
    buildFailed: "The slides could not be created.",
    needTopic: "Enter a topic first.",
    needOutline: "Write an outline first.",
  },
  de: {
    title: "Präsentation",
    intro: "Aus deinem Thema oder deiner Gliederung werden Folien. Du prüfst die Gliederung und " +
      "lädst am Ende die PowerPoint-Datei herunter.",
    stepContent: "Inhalt",
    stepOutline: "Gliederung",
    stepDone: "Fertig",
    heading: "Worum soll es gehen?",
    tabTopic: "Thema",
    tabMarkdown: "Gliederung",
    topicLabel: "Thema",
    topicPlaceholder: "Zum Beispiel: wie Honigbienen Blüten bestäuben",
    slidesLabel: "Anzahl der Folien",
    slidesHint: "Zwischen {lo} und {hi}. Leer lässt das Modell entscheiden.",
    markdownLabel: "Deine Gliederung als Markdown",
    markdownPlaceholder: "# Titel\n\nUntertitel\n\n## Erste Folie\n\nWas sie zeigt.",
    markdownHint: "Eine Überschrift je Folie, die Zeilen darunter sagen, was die Folie zeigt. " +
      "Eine Rolle in eckigen Klammern wählt das Layout, zum Beispiel [two_columns].",
    templateLabel: "Folienmaster",
    templateHelp: "Der Folienmaster legt Schrift, Farben und Aufbau aller Folien fest, mit festen " +
      "Platzhaltern für Titel, Text und Bilder.",
    languageLabel: "Sprache der Folien",
    languageEn: "Englisch",
    languageDe: "Deutsch",
    presenterLabel: "Name auf dem Deckblatt (optional)",
    presenterPlaceholder: "Zum Beispiel: Titel, Vorname und Nachname",
    instructionsLabel: "Inhaltliche Anweisung (optional)",
    instructionsPlaceholder: "Zum Beispiel: nur Kapitel 2, für Erstsemester, mit Beispielen aus der Praxis",
    styleLabel: "Anweisung für die Bilder",
    stylePlaceholder: "Zum Beispiel: flat vector illustration, muted blue and grey, white background",
    notesLabel: "Sprechernotizen zu jeder Folie erzeugen",
    notesHint: "Die Notizen landen in der Notizansicht von PowerPoint, nicht auf der Folie selbst.",
    imagesLabel: "Bilder erzeugen",
    modelTitle: "Modell",
    modelHint: "In der Umgebung ist kein Modell gesetzt. Trag einen OpenAI-kompatiblen Endpunkt und ein Modell ein.",
    next: "Gliederung erstellen",
    buildDirect: "Folien erzeugen",
    outlineTitle: "Die Gliederung",
    outlineLabel: "Gliederung",
    outlineHint: "Ändere die Titel, verschiebe Zeilen oder streiche eine Folie, bevor die Texte entstehen.",
    build: "Folien erzeugen",
    back: "Zurück",
    doneTitle: "Die Präsentation ist fertig",
    summary: "{n} Folien als PowerPoint-Datei.",
    download: "PowerPoint herunterladen",
    new: "Neue Präsentation",
    planning: "Die Gliederung entsteht",
    writing: "{done} von {total} Folientexten geschrieben",
    drawing: "Die Bilder werden erzeugt",
    building: "Die Datei wird gebaut",
    outlineFailed: "Die Gliederung konnte nicht erstellt werden.",
    buildFailed: "Die Folien konnten nicht erzeugt werden.",
    needTopic: "Trag zuerst ein Thema ein.",
    needOutline: "Schreib zuerst eine Gliederung.",
  },
};

const $ = (id) => document.getElementById(id);
const state = { lang: "en", info: null, tab: "topic", step: "content", timer: null, slides: [] };

function fill(text, values) {
  return String(text).replace(/\{(\w+)\}/g, (_, key) => String(values[key] ?? ""));
}

function t(key, values) {
  const node = TEXTS[state.lang][key];
  return values ? fill(node || key, values) : (node || key);
}

function paint() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-t]").forEach((el) => { el.textContent = t(el.dataset.t); });
  $("topic").placeholder = t("topicPlaceholder");
  $("markdown").placeholder = t("markdownPlaceholder");
  $("presenter").placeholder = t("presenterPlaceholder");
  $("instructions").placeholder = t("instructionsPlaceholder");
  $("styleText").placeholder = t("stylePlaceholder");
  if (state.info) {
    const hint = document.querySelector('[data-t="slidesHint"]');
    hint.textContent = t("slidesHint", { lo: state.info.min_slides, hi: state.info.max_slides });
  }
  document.querySelectorAll(".lang").forEach((b) => {
    b.classList.toggle("on", b.dataset.lang === state.lang);
  });
  paintSlides();
}

function paintSlides() {
  const list = $("slideList");
  list.innerHTML = "";
  state.slides.forEach((slide) => {
    const li = document.createElement("li");
    const num = document.createElement("span");
    num.className = "num";
    num.textContent = slide.number;
    const role = document.createElement("span");
    role.className = "role";
    role.textContent = slide.role.replace(/_/g, " ");
    const title = document.createElement("span");
    title.textContent = slide.title;
    li.append(num, role, title);
    list.append(li);
  });
}

function showStep(step) {
  state.step = step;
  document.querySelectorAll("#steps li").forEach((li) => {
    li.classList.toggle("on", li.dataset.step === step);
  });
  $("contentCard").hidden = step !== "content";
  $("startCard").hidden = step !== "content";
  $("modelCard").hidden = step !== "content" || (state.info && state.info.configured);
  $("outlineCard").hidden = step !== "outline";
  $("doneCard").hidden = step !== "done";
}

function showTab(tab) {
  state.tab = tab;
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("on", b.dataset.tab === tab));
  $("topicPane").hidden = tab !== "topic";
  $("markdownPane").hidden = tab !== "markdown";
  $("plan").hidden = tab !== "topic";
  $("skip").hidden = tab !== "markdown";
}

function fields() {
  return {
    base_url: $("baseUrl").value,
    model: $("modelName").value,
    api_key: $("apiKey").value,
    image_base_url: $("imageBaseUrl").value,
    image_model: $("imageModel").value,
    image_api_key: $("imageApiKey").value,
    language: $("language").value,
    template: $("template").value,
    presenter: $("presenter").value,
    instructions: $("instructions").value,
    style_text: $("styleText").value,
  };
}

function error(id, message) {
  const el = $(id);
  el.textContent = message || "";
  el.hidden = !message;
}

async function post(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || response.statusText);
  return data;
}

async function loadInfo() {
  const response = await fetch("/api/info");
  state.info = await response.json();
  const picker = $("template");
  picker.innerHTML = "";
  state.info.templates.forEach((entry) => {
    const option = document.createElement("option");
    option.value = entry.id;
    option.textContent = entry.name;
    picker.append(option);
  });
  if (state.info.template) picker.value = state.info.template;
  if (state.info.language) $("language").value = state.info.language;
  if (state.info.presenter) $("presenter").value = state.info.presenter;
  if (state.info.instructions) $("instructions").value = state.info.instructions;
  $("notes").checked = !!state.info.notes;
  $("images").checked = !!state.info.images;
  $("model").textContent = state.info.model || "";
  showStep("content");
}

async function plan() {
  const topic = $("topic").value.trim();
  if (!topic) { error("contentError", t("needTopic")); return; }
  error("contentError", "");
  $("plan").disabled = true;
  $("contentStatus").textContent = t("planning");
  try {
    const slides = parseInt($("slides").value, 10);
    const data = await post("/api/outline", {
      ...fields(), topic, slides: Number.isFinite(slides) ? slides : null,
    });
    $("outline").value = data.outline;
    showStep("outline");
  } catch (e) {
    error("contentError", `${t("outlineFailed")} ${e.message}`);
  } finally {
    $("plan").disabled = false;
    $("contentStatus").textContent = "";
  }
}

function toOutlineStep() {
  const text = $("markdown").value.trim();
  if (!text) { error("contentError", t("needOutline")); return; }
  error("contentError", "");
  $("outline").value = text;
  showStep("outline");
}

async function build() {
  const text = $("outline").value.trim();
  if (!text) { error("buildError", t("needOutline")); return; }
  error("buildError", "");
  $("build").disabled = true;
  $("buildStatus").textContent = t("building");
  try {
    await post("/api/build", {
      ...fields(), outline: text, notes: $("notes").checked, images: $("images").checked,
    });
    state.timer = setInterval(poll, 1000);
  } catch (e) {
    error("buildError", `${t("buildFailed")} ${e.message}`);
    $("build").disabled = false;
    $("buildStatus").textContent = "";
  }
}

function progressText(job) {
  if (job.step === "slides") return t("writing", { done: job.done, total: job.total });
  if (job.step === "pictures") return t("drawing");
  return t("building");
}

async function poll() {
  const response = await fetch("/api/status");
  const job = await response.json();
  if (job.state === "running") {
    $("buildStatus").textContent = progressText(job);
    return;
  }
  clearInterval(state.timer);
  state.timer = null;
  $("build").disabled = false;
  $("buildStatus").textContent = "";
  if (job.state === "error") {
    error("buildError", `${t("buildFailed")} ${job.error}`);
    return;
  }
  state.slides = job.slides;
  $("summary").textContent = t("summary", { n: job.slides.length });
  paintSlides();
  showPreviews(job.slides.length);
  showStep("done");
}

function showPreviews(count) {
  const box = $("previews");
  box.innerHTML = "";
  if (!state.info || !state.info.preview) return;
  for (let n = 1; n <= count; n += 1) {
    const img = document.createElement("img");
    img.src = `/api/preview/${n}?v=${Date.now()}`;
    img.alt = `${t("stepDone")} ${n}`;
    img.loading = "lazy";
    img.onerror = () => img.remove();
    box.append(img);
  }
}

document.querySelectorAll(".lang").forEach((b) => {
  b.addEventListener("click", () => { state.lang = b.dataset.lang; paint(); });
});
document.querySelectorAll(".tab").forEach((b) => {
  b.addEventListener("click", () => showTab(b.dataset.tab));
});
$("plan").addEventListener("click", plan);
$("skip").addEventListener("click", toOutlineStep);
$("build").addEventListener("click", build);
$("back").addEventListener("click", () => showStep("content"));
$("again").addEventListener("click", () => { state.slides = []; showStep("content"); });

showTab("topic");
paint();
loadInfo().then(paint);
