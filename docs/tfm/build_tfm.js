// Genera la memoria del TFM en Word a partir de tfm.md.
// Uso: node docs/tfm/build_tfm.js   (desde la raíz de poc-almagentic-core)
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, LevelFormat, PageBreak, TableOfContents, Header, Footer,
  PageNumber, ImageRun, ExternalHyperlink, TabStopType,
} = require("docx");

const DIR = __dirname;
const SRC = path.join(DIR, "tfm.md");
const OUT = path.join(DIR, "TFM-ALM-agentico.docx");

const META = {
  titulo: "ALM agéntico",
  subtitulo: "Diseño y validación de un ciclo de vida de aplicaciones gobernado con agentes de IA",
  tipo: "Trabajo Fin de Máster · Máster en Inteligencia Artificial",
  autor: "[Nombre del autor]",
  tutor: "[Nombre del tutor]",
  fecha: "Octubre de 2026",
  version: "Versión de trabajo · se actualiza al cerrar cada tarea de la POC",
};

const FONT = "Calibri";
const MONO = "Consolas";
const ACCENT = "0D5C4F";
const MUTED = "5B6964";
const LINE = "C9D3CF";
const HEAD_FILL = "E3EEEA";
const PAGE_W = 11906, MARGIN = 1418; // A4, 2,5 cm
const CONTENT_W = PAGE_W - 2 * MARGIN;

// ---------- texto en línea: **negrita**, *cursiva*, `código`, [enlace](url) ----------
function inline(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let last = 0, m;
  const push = (t, o = {}) => t && out.push(new TextRun({ text: t, font: FONT, ...base, ...o }));
  while ((m = re.exec(text))) {
    push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) push(tok.slice(2, -2), { bold: true });
    else if (tok.startsWith("`")) out.push(new TextRun({ text: tok.slice(1, -1), font: MONO, size: (base.size || 22) - 2, color: "2E3A36" }));
    else if (tok.startsWith("[")) {
      const [, label, url] = tok.match(/\[([^\]]+)\]\(([^)]+)\)/);
      out.push(new ExternalHyperlink({ link: url, children: [new TextRun({ text: label, style: "Hyperlink", font: FONT, ...base })] }));
    } else push(tok.slice(1, -1), { italics: true });
    last = m.index + tok.length;
  }
  push(text.slice(last));
  // URLs sueltas como enlaces
  return out.flatMap(r => r);
}

function linkify(text, base) {
  const parts = text.split(/(https?:\/\/\S+)/g);
  return parts.flatMap(p => /^https?:\/\//.test(p)
    ? [new ExternalHyperlink({ link: p, children: [new TextRun({ text: p, style: "Hyperlink", font: FONT, ...base })] })]
    : inline(p, base));
}

// ---------- tablas ----------
function cell(text, { header = false, width }) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: header ? { fill: HEAD_FILL, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ spacing: { before: 0, after: 0, line: 252 }, children: inline(text, { size: 18, bold: header || undefined }) })],
  });
}

function table(rows) {
  const parsed = rows.map(r => r.trim().replace(/^\||\|$/g, "").split("|").map(c => c.trim()));
  const header = parsed[0];
  const body = parsed.slice(2);
  const n = header.length;
  // anchos proporcionales a la longitud media del texto de cada columna, con mínimo
  const lens = header.map((_, i) => Math.max(6, ...[header, ...body].map(r => (r[i] || "").length)) );
  const avg = header.map((_, i) => [header, ...body].reduce((s, r) => s + Math.min((r[i] || "").length, 60), 0) / (body.length + 1));
  const weights = avg.map((a, i) => Math.max(a, 5) + Math.min(lens[i], 12) * 0.3);
  const total = weights.reduce((a, b) => a + b, 0);
  let widths = weights.map(w => Math.max(700, Math.round(CONTENT_W * w / total)));
  const diff = CONTENT_W - widths.reduce((a, b) => a + b, 0);
  widths[widths.indexOf(Math.max(...widths))] += diff;
  const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: widths,
    borders: { top: border, bottom: border, left: border, right: border, insideHorizontal: border, insideVertical: border },
    rows: [
      new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, { header: true, width: widths[i] })) }),
      ...body.map(r => new TableRow({ cantSplit: true, children: Array.from({ length: n }, (_, i) => cell(r[i] || "", { width: widths[i] })) })),
    ],
  });
}

// ---------- bloques ----------
function codeBlock(lines) {
  return lines.map((l, i) => new Paragraph({
    shading: { fill: "F2F4F3", type: ShadingType.CLEAR, color: "auto" },
    spacing: { before: i === 0 ? 120 : 0, after: i === lines.length - 1 ? 160 : 0, line: 240 },
    indent: { left: 200, right: 200 },
    children: [new TextRun({ text: l || " ", font: MONO, size: 17, color: "1F2A27" })],
  }));
}

function callout(text) {
  return new Paragraph({
    spacing: { before: 120, after: 160 },
    indent: { left: 240, right: 120 },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: ACCENT, space: 10 } },
    shading: { fill: "EEF5F3", type: ShadingType.CLEAR, color: "auto" },
    children: inline(text, { size: 21 }),
  });
}

let figN = 0;
function figure(caption, file) {
  const png = fs.readFileSync(path.join(DIR, file));
  const w = png.readUInt32BE(16), h = png.readUInt32BE(20);
  const maxW = 600, maxH = 420; // px a 96 dpi aprox.
  const scale = Math.min(maxW / w, maxH / h);
  figN++;
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200, after: 60 }, keepNext: true,
      children: [new ImageRun({ type: "png", data: png, transformation: { width: Math.round(w * scale), height: Math.round(h * scale) },
        altText: { title: caption, description: caption, name: path.basename(file) } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
      children: [new TextRun({ text: caption, italics: true, size: 18, color: MUTED, font: FONT })] }),
  ];
}

// ---------- markdown → bloques ----------
function parse(md) {
  const lines = md.split("\n");
  const out = [];
  let i = 0, firstH1 = true;
  while (i < lines.length) {
    const l = lines[i];
    if (!l.trim()) { i++; continue; }
    if (l.startsWith("```")) {
      const buf = []; i++;
      while (i < lines.length && !lines[i].startsWith("```")) buf.push(lines[i++]);
      i++; out.push(...codeBlock(buf)); continue;
    }
    if (l.startsWith("# ")) {
      out.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: !firstH1, children: [new TextRun({ text: l.slice(2), font: FONT })] }));
      firstH1 = false; i++; continue;
    }
    if (l.startsWith("## ")) { out.push(new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, children: [new TextRun({ text: l.slice(3), font: FONT })] })); i++; continue; }
    if (l.startsWith("### ")) { out.push(new Paragraph({ heading: HeadingLevel.HEADING_3, keepNext: true, children: [new TextRun({ text: l.slice(4), font: FONT })] })); i++; continue; }
    if (l.startsWith("![")) {
      const [, cap, file] = l.match(/!\[([^\]]*)\]\(([^)]+)\)/);
      out.push(...figure(cap, file)); i++; continue;
    }
    if (l.startsWith("|")) {
      const buf = [];
      while (i < lines.length && lines[i].startsWith("|")) buf.push(lines[i++]);
      out.push(table(buf), new Paragraph({ spacing: { after: 120 }, children: [] })); continue;
    }
    if (l.startsWith("> ")) {
      const buf = [];
      while (i < lines.length && lines[i].startsWith(">")) buf.push(lines[i++].replace(/^>\s?/, ""));
      out.push(callout(buf.join(" "))); continue;
    }
    if (/^\s*- /.test(l)) {
      while (i < lines.length && /^\s*- /.test(lines[i])) {
        const lvl = lines[i].match(/^(\s*)/)[1].length >= 2 ? 1 : 0;
        out.push(new Paragraph({ numbering: { reference: "bullets", level: lvl }, spacing: { after: 60 }, children: inline(lines[i].replace(/^\s*- /, "")) }));
        i++;
      }
      continue;
    }
    if (/^\d+\. /.test(l)) {
      const ref = "num" + (numRefs.length);
      numRefs.push(ref);
      while (i < lines.length && /^\d+\. /.test(lines[i])) {
        out.push(new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 60 }, children: inline(lines[i].replace(/^\d+\. /, "")) }));
        i++;
      }
      continue;
    }
    // párrafo (referencias con [n] y URL sueltas)
    const isRef = /^\[\d+\]/.test(l);
    out.push(new Paragraph({
      spacing: { after: isRef ? 100 : 140, line: 288 },
      alignment: isRef ? AlignmentType.LEFT : AlignmentType.JUSTIFIED,
      indent: isRef ? { left: 480, hanging: 480 } : undefined,
      children: linkify(l, isRef ? { size: 19 } : {}),
    }));
    i++;
  }
  return out;
}

const numRefs = [];

// ---------- portada ----------
function cover() {
  const p = (text, o = {}) => new Paragraph({ alignment: AlignmentType.LEFT, ...o.para, children: [new TextRun({ text, font: FONT, ...o.run })] });
  return [
    p("", { para: { spacing: { before: 1800 } } }),
    p(META.tipo.toUpperCase(), { run: { size: 20, color: MUTED, bold: true, characterSpacing: 20 } }),
    new Paragraph({ spacing: { before: 200, after: 120 }, border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: ACCENT, space: 8 } },
      children: [new TextRun({ text: META.titulo, font: FONT, size: 64, bold: true, color: "17211E" })] }),
    p(META.subtitulo, { run: { size: 30, color: "2E3A36" }, para: { spacing: { after: 1600 } } }),
    p(`Autor: ${META.autor}`, { run: { size: 24 }, para: { spacing: { after: 80 } } }),
    p(`Tutor: ${META.tutor}`, { run: { size: 24 }, para: { spacing: { after: 80 } } }),
    p(META.fecha, { run: { size: 24 }, para: { spacing: { after: 600 } } }),
    p(META.version, { run: { size: 18, italics: true, color: MUTED } }),
    p("Repositorios: github.com/acbacb77/poc-almagentic-app · -core · -gitops", { run: { size: 18, color: MUTED } }),
    new Paragraph({ children: [new PageBreak()] }),
    new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: "Índice", font: FONT })] }),
    new TableOfContents("Índice", { hyperlink: true, headingStyleRange: "1-2" }),
    new Paragraph({ spacing: { before: 200 }, children: [new TextRun({ text: "Si el índice aparece vacío, en Word: clic derecho sobre él → Actualizar campos.", italics: true, size: 18, color: MUTED, font: FONT })] }),
  ];
}

// ---------- documento ----------
const body = parse(fs.readFileSync(SRC, "utf8"));
const numbering = {
  config: [
    { reference: "bullets", levels: [
      { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
      { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1000, hanging: 270 } } } },
    ] },
    ...numRefs.map(ref => ({ reference: ref, levels: [
      { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 320 } } } },
    ] })),
  ],
};

const doc = new Document({
  creator: META.autor,
  title: `${META.titulo}: ${META.subtitulo}`,
  description: META.tipo,
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: FONT, size: 22, color: "1F2A27" }, paragraph: { spacing: { line: 288 } } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, color: ACCENT, font: FONT }, paragraph: { spacing: { before: 0, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: "17211E", font: FONT }, paragraph: { spacing: { before: 320, after: 140 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, color: ACCENT, font: FONT }, paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering,
  sections: [
    { properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
      children: cover() },
    { properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN }, pageNumbers: { start: 1 } } },
      headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: `${META.titulo} · ${META.tipo}`, size: 16, color: MUTED, font: FONT })] })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ children: ["Página ", PageNumber.CURRENT], size: 16, color: MUTED, font: FONT })] })] }) },
      children: body },
  ],
});

Packer.toBuffer(doc).then(buf => { fs.writeFileSync(OUT, buf); console.log("Escrito", OUT); });
