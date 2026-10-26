"use strict";

// The texts of the page in both languages, the same wording the tool uses elsewhere.
const TEXTS = {
  en: {
    title: "Presentation",
    intro: "Your topic, your documents or your outline becomes slides. One click builds the " +
      "whole deck and you download the PowerPoint file at the end.",
    stepContent: "Content",
    stepDone: "Done",
    heading: "What is it about?",
    tabTopic: "Topic",
    tabMaterial: "Documents",
    tabMarkdown: "Outline",
    inUseTopic: "In use: the topic. The model plans the deck from what it knows about it.",
    inUseMaterial: "In use: your documents. The deck is planned over what they say.",
    inUseMarkdown: "In use: your own outline. No outline is planned, the slides are written straight away.",
    dropLabel: "Drop your documents here",
    dropHint: "or click to choose. {kinds}, at most {files} files.",
    materialSlidesHint: "Empty lets the amount of material decide.",
    materialRead: "Read: {files} file(s), {pages} page(s), {chars} characters.",
    materialShortened: "That is more than one call may carry ({limit} characters), so the deck " +
      "was planned through the topics of the material.",
    needFiles: "Choose at least one document.",
    reading: "The documents are being read and planned",
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
    masterUpload: "Upload your own slide master",
    masterUploaded: "{name} (uploaded)",
    masterReading: "The slide master is being checked",
    masterUsed: "{used} of {layouts} layouts are used.",
    masterSkipped: "Skipped, because they have no title field or vertical text: {names}.",
    masterFailed: "The slide master cannot be used.",
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
    build: "Create slides",
    doneTitle: "The presentation is done",
    summary: "{n} slides as a PowerPoint file.",
    infoModel: "Text model",
    infoImageModel: "Image model",
    infoTemplate: "Slide master",
    infoLanguage: "Language",
    infoInstructions: "Instruction",
    infoStyleText: "Image style",
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
    intro: "Aus deinem Thema, deinen Dokumenten oder deiner Gliederung werden Folien. Ein Klick " +
      "baut die ganze Präsentation und du lädst am Ende die PowerPoint-Datei herunter.",
    stepContent: "Inhalt",
    stepDone: "Fertig",
    heading: "Worum soll es gehen?",
    tabTopic: "Thema",
    tabMaterial: "Dokumente",
    tabMarkdown: "Gliederung",
    inUseTopic: "Verwendet wird das Thema. Das Modell plant die Folien aus dem, was es dazu weiß.",
    inUseMaterial: "Verwendet werden deine Dokumente. Die Folien entstehen aus dem, was darin steht.",
    inUseMarkdown: "Verwendet wird deine eigene Gliederung. Es wird nichts geplant, die Texte entstehen direkt.",
    dropLabel: "Dokumente hier ablegen",
    dropHint: "oder klicken zum Auswählen. {kinds}, höchstens {files} Dateien.",
    materialSlidesHint: "Leer lässt die Menge des Materials entscheiden.",
    materialRead: "Gelesen: {files} Datei(en), {pages} Seite(n), {chars} Zeichen.",
    materialShortened: "Das ist mehr, als ein Aufruf tragen kann ({limit} Zeichen). Die Folien " +
      "wurden deshalb über die Themen des Materials geplant.",
    needFiles: "Wähle mindestens ein Dokument.",
    reading: "Die Dokumente werden gelesen und geplant",
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
    masterUpload: "Eigenen Folienmaster hochladen",
    masterUploaded: "{name} (hochgeladen)",
    masterReading: "Der Folienmaster wird geprüft",
    masterUsed: "{used} von {layouts} Layouts werden genutzt.",
    masterSkipped: "Übersprungen, weil ihnen ein Titelfeld fehlt oder der Text senkrecht läuft: {names}.",
    masterFailed: "Der Folienmaster kann nicht verwendet werden.",
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
    build: "Folien erstellen",
    doneTitle: "Die Präsentation ist fertig",
    summary: "{n} Folien als PowerPoint-Datei.",
    infoModel: "Textmodell",
    infoImageModel: "Bildmodell",
    infoTemplate: "Folienmaster",
    infoLanguage: "Sprache",
    infoInstructions: "Hinweis",
    infoStyleText: "Bildstil",
    download: "PowerPoint herunterladen",
    new: "Neue Präsentation",
    planning: "Die Gliederung entsteht",
    writing: "{done} von {total} Folientexten geschrieben",
    drawing: "Die Bilder werden erzeugt",
    building: "Die Datei wird gebaut",
    outlineFailed: "Die Gliederung konnte nicht erstellt werden.",
    buildFailed: "Die Folien konnten nicht erstellt werden.",
    needTopic: "Trag zuerst ein Thema ein.",
    needOutline: "Schreib zuerst eine Gliederung.",
  },
};

const $ = (id) => document.getElementById(id);
const state = { lang: "en", info: null, deck: null, tab: "topic", step: "content",
                timer: null, slides: [], files: [], material: null, masters: [] };

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
    $("dropHint").textContent = t("dropHint", {
      kinds: (state.info.extensions || []).join(" "), files: state.info.max_material_files });
  }
  $("inUse").textContent = t(`inUse${state.tab[0].toUpperCase()}${state.tab.slice(1)}`);
  paintFiles();
  paintMaterial();
  paintMaster();
  document.querySelectorAll(".lang").forEach((b) => {
    b.classList.toggle("on", b.dataset.lang === state.lang);
  });
  paintSlides();
}

// Every field /api/status reports about the finished deck, in the order the card shows them.
const INFO_FIELDS = [
  ["model", "infoModel"],
  ["image_model", "infoImageModel"],
  ["template", "infoTemplate"],
  ["language", "infoLanguage"],
  ["instructions", "infoInstructions"],
  ["style_text", "infoStyleText"],
];

function paintInfo() {
  const box = $("deckInfo");
  box.innerHTML = "";
  const info = state.deck || {};
  INFO_FIELDS.forEach(([key, label]) => {
    const value = info[key];
    if (!value) return;
    const term = document.createElement("dt");
    term.textContent = t(label);
    const text = document.createElement("dd");
    text.textContent = value;
    box.append(term, text);
  });
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
  $("doneCard").hidden = step !== "done";
}

function showTab(tab) {
  state.tab = tab;
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("on", b.dataset.tab === tab));
  $("topicPane").hidden = tab !== "topic";
  $("materialPane").hidden = tab !== "material";
  $("markdownPane").hidden = tab !== "markdown";
  $("inUse").textContent = t(`inUse${tab[0].toUpperCase()}${tab.slice(1)}`);
}

function size(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function number(value) {
  return new Intl.NumberFormat(state.lang === "de" ? "de-DE" : "en-GB").format(value);
}

function paintFiles() {
  const list = $("fileList");
  list.innerHTML = "";
  state.files.forEach((file) => {
    const li = document.createElement("li");
    const name = document.createElement("span");
    name.textContent = file.name;
    const bytes = document.createElement("span");
    bytes.className = "size";
    bytes.textContent = size(file.size);
    li.append(name, bytes);
    list.append(li);
  });
}

// What was really read out of the documents, so the budget is no surprise.
function paintMaterial() {
  const box = $("materialInfo");
  const found = state.material;
  if (!found) { box.textContent = ""; return; }
  let text = t("materialRead", { files: found.material.files.length,
                                 pages: found.material.pages,
                                 chars: number(found.material.chars) });
  if (found.shortened) text += ` ${t("materialShortened", { limit: number(found.window_chars) })}`;
  box.textContent = text;
}

function addFiles(chosen) {
  const most = (state.info && state.info.max_material_files) || 10;
  state.files = Array.from(chosen).slice(0, most);
  state.material = null;
  paintFiles();
  paintMaterial();
}

// Every uploaded master as one more entry of the picker, with what the analysis made of the chosen one.
function paintMaster() {
  const picker = $("template");
  const chosen = picker.value;
  picker.querySelectorAll("option[data-upload]").forEach((option) => option.remove());
  state.masters.forEach((master) => {
    const option = document.createElement("option");
    option.value = master.id;
    option.dataset.upload = "1";
    option.textContent = t("masterUploaded", { name: master.name });
    picker.append(option);
  });
  if (chosen) picker.value = chosen;
  const master = state.masters.find((item) => item.id === picker.value);
  let text = "";
  if (master && master.layouts) {
    text = t("masterUsed", { used: master.used, layouts: master.layouts });
    if (master.skipped.length) {
      text += ` ${t("masterSkipped", { names: master.skipped.join(", ") })}`;
    }
  }
  $("masterInfo").textContent = text;
}

async function uploadMaster(file) {
  if (!file) return;
  error("masterError", "");
  $("masterInfo").textContent = t("masterReading");
  try {
    const body = new FormData();
    body.append("file", file);
    const response = await fetch("/api/template", { method: "POST", body });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || response.statusText);
    state.masters = state.masters.filter((item) => item.id !== data.id).concat([data]);
    $("template").value = "";
    paintMaster();
    $("template").value = data.id;
    paintMaster();
  } catch (e) {
    $("masterInfo").textContent = "";
    error("masterError", `${t("masterFailed")} ${e.message}`);
    paintMaster();
  } finally {
    $("masterFile").value = "";
  }
}

async function planFromMaterial() {
  $("contentStatus").textContent = t("reading");
  const body = new FormData();
  state.files.forEach((file) => body.append("files", file));
  body.append("fields", JSON.stringify(fields()));
  const slides = parseInt($("materialSlides").value, 10);
  if (Number.isFinite(slides)) body.append("slides", String(slides));
  const response = await fetch("/api/material", { method: "POST", body });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || response.statusText);
  state.material = data;
  paintMaterial();
  return data.outline;
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
  state.masters = (state.info.uploads || []).map((item) => ({ ...item, layouts: 0, used: 0, skipped: [] }));
  paintMaster();
  if (state.info.template) picker.value = state.info.template;
  if (state.info.language) $("language").value = state.info.language;
  if (state.info.presenter) $("presenter").value = state.info.presenter;
  if (state.info.instructions) $("instructions").value = state.info.instructions;
  $("notes").checked = !!state.info.notes;
  $("images").checked = !!state.info.images;
  $("model").textContent = state.info.model || "";
  showStep("content");
}

async function planFromTopic(topic) {
  $("contentStatus").textContent = t("planning");
  const slides = parseInt($("slides").value, 10);
  const data = await post("/api/outline", {
    ...fields(), topic, slides: Number.isFinite(slides) ? slides : null,
  });
  return data.outline;
}

// The one button: plans the outline where there is none yet, then builds the deck.
async function build() {
  const topic = $("topic").value.trim();
  const markdown = $("markdown").value.trim();
  if (state.tab === "topic" && !topic) { error("contentError", t("needTopic")); return; }
  if (state.tab === "material" && !state.files.length) { error("contentError", t("needFiles")); return; }
  if (state.tab === "markdown" && !markdown) { error("contentError", t("needOutline")); return; }
  error("contentError", "");
  $("build").disabled = true;
  let text;
  try {
    if (state.tab === "topic") text = await planFromTopic(topic);
    else if (state.tab === "material") text = await planFromMaterial();
    else text = markdown;
  } catch (e) {
    error("contentError", `${t("outlineFailed")} ${e.message}`);
    $("build").disabled = false;
    $("contentStatus").textContent = "";
    return;
  }
  $("contentStatus").textContent = t("building");
  try {
    await post("/api/build", {
      ...fields(), outline: text, notes: $("notes").checked, images: $("images").checked,
    });
    state.timer = setInterval(poll, 1000);
  } catch (e) {
    error("contentError", `${t("buildFailed")} ${e.message}`);
    $("build").disabled = false;
    $("contentStatus").textContent = "";
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
    $("contentStatus").textContent = progressText(job);
    return;
  }
  clearInterval(state.timer);
  state.timer = null;
  $("build").disabled = false;
  $("contentStatus").textContent = "";
  if (job.state === "error") {
    error("contentError", `${t("buildFailed")} ${job.error}`);
    return;
  }
  state.slides = job.slides;
  state.deck = job.info || {};
  $("summary").textContent = t("summary", { n: job.slides.length });
  paintSlides();
  paintInfo();
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
$("files").addEventListener("change", (event) => addFiles(event.target.files));
$("drop").addEventListener("dragover", (event) => {
  event.preventDefault();
  $("drop").classList.add("over");
});
$("drop").addEventListener("dragleave", () => $("drop").classList.remove("over"));
$("drop").addEventListener("drop", (event) => {
  event.preventDefault();
  $("drop").classList.remove("over");
  addFiles(event.dataTransfer.files);
});
$("build").addEventListener("click", build);
$("masterFile").addEventListener("change", (event) => uploadMaster(event.target.files[0]));
$("template").addEventListener("change", paintMaster);
$("again").addEventListener("click", () => { state.slides = []; showStep("content"); });

showTab("topic");
paint();
loadInfo().then(paint);
