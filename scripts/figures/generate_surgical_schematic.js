const fs = require("fs");
const path = require("path");
const PptxGenJS = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..");
const OUT = path.join(ROOT, "docs", "figures");
fs.mkdirSync(OUT, { recursive: true });

const pptx = new PptxGenJS();
pptx.defineLayout({ name: "JAR_FIGURE", width: 7.20, height: 4.65 });
pptx.layout = "JAR_FIGURE";
pptx.author = "Shanbin Zheng; Xin Liu; Jirong Shen; Tianwei Xia";
pptx.subject = "PVIBGT and SHD-IBG schematic workflows for ONFH";
pptx.title = "Schematic comparison of PVIBGT and SHD-IBG";
pptx.company = "ONFH ROI-FEA research team";
pptx.theme = {
  headFontFace: "Arial",
  bodyFontFace: "Arial",
  lang: "en-US",
};

const S = pptx.ShapeType;
const C = {
  ink: "1F2933",
  muted: "5E6A72",
  line: "C6D0D6",
  grid: "E9EEF2",
  paper: "FFFFFF",
  panel: "F8FAFB",
  teal: "008C8C",
  tealLight: "E5F5F4",
  green: "009E73",
  greenLight: "E7F6EF",
  orange: "D98324",
  orangeLight: "FFF1DA",
  red: "D55E00",
  redLight: "FCE8DF",
  bone: "F6D7B0",
  boneLine: "A67C52",
  cartilage: "C9E7EF",
  vessel: "C83E4D",
};

function text(slide, value, x, y, w, h, opts = {}) {
  slide.addText(value, {
    x,
    y,
    w,
    h,
    margin: opts.margin ?? 0.02,
    fontFace: opts.fontFace || "Arial",
    fontSize: opts.size || 6.8,
    bold: Boolean(opts.bold),
    italic: Boolean(opts.italic),
    color: opts.color || C.ink,
    align: opts.align || "left",
    valign: opts.valign || "mid",
    fit: "shrink",
    breakLine: false,
    paraSpaceAfterPt: 0,
    charSpacing: 0,
  });
}

function rect(slide, x, y, w, h, fill, line = fill, width = 0.6, radius = false) {
  slide.addShape(radius ? S.roundRect : S.rect, {
    x,
    y,
    w,
    h,
    rectRadius: radius ? 0.03 : undefined,
    fill: { color: fill },
    line: { color: line, width },
  });
}

function ellipse(slide, x, y, w, h, fill, line = fill, width = 0.6, transparency = 0) {
  slide.addShape(S.ellipse, {
    x,
    y,
    w,
    h,
    fill: { color: fill, transparency },
    line: { color: line, width },
  });
}

function line(slide, x1, y1, x2, y2, color = C.line, width = 0.8, dash = "solid", arrow = false) {
  slide.addShape(S.line, {
    x: Math.min(x1, x2),
    y: Math.min(y1, y2),
    w: Math.abs(x2 - x1),
    h: Math.abs(y2 - y1),
    flipH: x2 < x1,
    flipV: y2 < y1,
    line: {
      color,
      width,
      dashType: dash,
      endArrowType: arrow ? "triangle" : "none",
    },
  });
}

function arc(slide, x, y, w, h, color, width = 0.8, rotate = 0, dash = "solid") {
  slide.addShape(S.arc, {
    x,
    y,
    w,
    h,
    rotate,
    fill: { color: C.paper, transparency: 100 },
    line: { color, width, dashType: dash },
  });
}

function arrow(slide, x1, y1, x2, y2, color = C.line) {
  line(slide, x1, y1, x2, y2, color, 0.9, "solid", true);
}

function stepBadge(slide, n, x, y, color) {
  ellipse(slide, x, y, 0.18, 0.18, color, color, 0.4);
  text(slide, String(n), x, y + 0.007, 0.18, 0.13, {
    size: 6.4,
    bold: true,
    color: C.paper,
    align: "center",
  });
}

function tile(slide, n, title, x, y, w, h, color, fill, drawIcon) {
  rect(slide, x, y, w, h, C.paper, C.line, 0.55, true);
  rect(slide, x + 0.04, y + 0.04, w - 0.08, 0.08, fill, fill, 0.2, true);
  stepBadge(slide, n, x + 0.09, y + 0.18, color);
  drawIcon(slide, x + 0.27, y + 0.26, w - 0.54, 0.48);
  rect(slide, x + 0.08, y + h - 0.28, w - 0.16, 0.23, C.paper, C.paper, 0.1, true);
  text(slide, title, x + 0.12, y + h - 0.25, w - 0.24, 0.18, {
    size: 5.2,
    bold: true,
    color: C.ink,
    align: "center",
  });
}

function panelHeader(slide, panel, title, subtitle, x, y, w, color, fill) {
  rect(slide, x, y, w, 0.30, fill, color, 0.55, true);
  ellipse(slide, x + 0.06, y + 0.055, 0.18, 0.18, color, color, 0.4);
  text(slide, panel, x + 0.06, y + 0.065, 0.18, 0.13, {
    size: 6.8,
    bold: true,
    color: C.paper,
    align: "center",
  });
  text(slide, title, x + 0.30, y + 0.04, 1.70, 0.12, {
    size: 7.6,
    bold: true,
    color,
  });
  text(slide, subtitle, x + 2.04, y + 0.04, w - 2.12, 0.12, {
    size: 5.5,
    color: C.muted,
    align: "right",
  });
}

function drawPelvis(slide, x, y, s, color = C.boneLine) {
  arc(slide, x + 0.13 * s, y + 0.05 * s, 0.47 * s, 0.42 * s, color, 1.0, -24);
  arc(slide, x + 0.01 * s, y + 0.16 * s, 0.46 * s, 0.38 * s, color, 0.8, 18);
  ellipse(slide, x + 0.31 * s, y + 0.31 * s, 0.22 * s, 0.18 * s, C.paper, color, 0.85);
  ellipse(slide, x + 0.36 * s, y + 0.36 * s, 0.08 * s, 0.06 * s, C.cartilage, C.cartilage, 0.2);
}

function drawFemur(slide, x, y, s, opts = {}) {
  const headX = x + 0.36 * s;
  const headY = y + 0.31 * s;
  ellipse(slide, headX, headY, 0.18 * s, 0.18 * s, C.bone, C.boneLine, 0.75);
  line(slide, x + 0.50 * s, y + 0.43 * s, x + 0.72 * s, y + 0.59 * s, C.boneLine, 3.2);
  line(slide, x + 0.66 * s, y + 0.56 * s, x + 0.70 * s, y + 0.83 * s, C.boneLine, 5.4);
  ellipse(slide, x + 0.61 * s, y + 0.52 * s, 0.12 * s, 0.15 * s, C.bone, C.boneLine, 0.6);
  if (opts.lesion) {
    ellipse(slide, headX + 0.055 * s, headY + 0.025 * s, 0.07 * s, 0.055 * s, C.redLight, C.red, 0.45);
  }
  if (opts.cavity) {
    ellipse(slide, headX + 0.05 * s, headY + 0.025 * s, 0.075 * s, 0.055 * s, C.paper, C.red, 0.65);
  }
  if (opts.greenGraft) {
    ellipse(slide, headX + 0.047 * s, headY + 0.023 * s, 0.083 * s, 0.060 * s, C.greenLight, C.green, 0.65);
  }
  if (opts.orangeGraft) {
    for (let i = 0; i < 5; i += 1) {
      ellipse(
        slide,
        headX + (0.052 + 0.015 * (i % 3)) * s,
        headY + (0.025 + 0.018 * Math.floor(i / 3)) * s,
        0.017 * s,
        0.014 * s,
        C.orangeLight,
        C.orange,
        0.35,
      );
    }
  }
}

function drawReducedHip(slide, x, y, w, h, opts = {}) {
  const s = Math.min(w, h) / 0.86;
  drawPelvis(slide, x + 0.06 * s, y + 0.02 * s, s);
  drawFemur(slide, x + 0.08 * s, y + 0.03 * s, s, opts);
}

function drawDislocatedHip(slide, x, y, w, h, opts = {}) {
  const s = Math.min(w, h) / 0.86;
  drawPelvis(slide, x + 0.02 * s, y + 0.02 * s, s);
  drawFemur(slide, x + 0.31 * s, y + 0.08 * s, s, opts);
  arc(slide, x + 0.43 * s, y + 0.21 * s, 0.22 * s, 0.20 * s, C.orange, 0.9, 10, "dash");
  arrow(slide, x + 0.47 * s, y + 0.35 * s, x + 0.35 * s, y + 0.29 * s, C.orange);
}

function drawVessel(slide, points, color = C.vessel, width = 1.2) {
  for (let i = 0; i < points.length - 1; i += 1) {
    line(slide, points[i][0], points[i][1], points[i + 1][0], points[i + 1][1], color, width);
  }
  points.forEach(([px, py]) => ellipse(slide, px - 0.012, py - 0.012, 0.024, 0.024, color, color, 0.2));
}

function iconFlapHarvest(slide, x, y) {
  drawPelvis(slide, x + 0.13, y + 0.00, 0.62);
  rect(slide, x + 0.38, y + 0.09, 0.17, 0.06, C.greenLight, C.green, 0.65, true);
  line(slide, x + 0.37, y + 0.09, x + 0.56, y + 0.18, C.green, 0.8, "dash");
  drawVessel(slide, [[x + 0.42, y + 0.19], [x + 0.37, y + 0.27], [x + 0.31, y + 0.35]], C.vessel, 0.85);
}

function iconPedicleTransfer(slide, x, y) {
  drawReducedHip(slide, x + 0.16, y - 0.02, 0.56, 0.56, { lesion: true });
  rect(slide, x + 0.15, y + 0.07, 0.15, 0.05, C.greenLight, C.green, 0.55, true);
  arrow(slide, x + 0.30, y + 0.12, x + 0.47, y + 0.28, C.green);
  drawVessel(slide, [[x + 0.23, y + 0.14], [x + 0.31, y + 0.22], [x + 0.46, y + 0.34]], C.vessel, 0.75);
}

function iconDebrideReduced(slide, x, y) {
  drawReducedHip(slide, x + 0.17, y - 0.02, 0.56, 0.56, { cavity: true });
  line(slide, x + 0.56, y + 0.12, x + 0.47, y + 0.28, C.ink, 1.25);
  ellipse(slide, x + 0.53, y + 0.08, 0.06, 0.04, C.paper, C.ink, 0.45);
}

function iconFlapImplant(slide, x, y) {
  drawReducedHip(slide, x + 0.17, y - 0.02, 0.56, 0.56, { greenGraft: true });
  drawVessel(slide, [[x + 0.25, y + 0.13], [x + 0.35, y + 0.22], [x + 0.47, y + 0.34]], C.vessel, 0.8);
  line(slide, x + 0.48, y + 0.33, x + 0.54, y + 0.38, C.green, 0.9);
}

function iconTrochanterHarvest(slide, x, y) {
  drawReducedHip(slide, x + 0.17, y - 0.02, 0.56, 0.56, { lesion: true });
  line(slide, x + 0.53, y + 0.35, x + 0.62, y + 0.27, C.orange, 1.1, "dash");
  rect(slide, x + 0.59, y + 0.26, 0.07, 0.05, C.orangeLight, C.orange, 0.35, true);
  ellipse(slide, x + 0.30, y + 0.42, 0.021, 0.017, C.orangeLight, C.orange, 0.3);
  ellipse(slide, x + 0.34, y + 0.43, 0.019, 0.016, C.orangeLight, C.orange, 0.3);
  ellipse(slide, x + 0.38, y + 0.42, 0.020, 0.017, C.orangeLight, C.orange, 0.3);
}

function iconDislocation(slide, x, y) {
  drawDislocatedHip(slide, x + 0.08, y - 0.02, 0.66, 0.56, { lesion: true });
}

function iconDebrideDislocated(slide, x, y) {
  drawDislocatedHip(slide, x + 0.08, y - 0.02, 0.66, 0.56, { cavity: true });
  line(slide, x + 0.60, y + 0.11, x + 0.52, y + 0.27, C.ink, 1.25);
  ellipse(slide, x + 0.57, y + 0.07, 0.06, 0.04, C.paper, C.ink, 0.45);
}

function iconImpaction(slide, x, y) {
  drawDislocatedHip(slide, x + 0.08, y - 0.02, 0.66, 0.56, { orangeGraft: true });
  line(slide, x + 0.58, y + 0.18, x + 0.50, y + 0.29, C.orange, 1.0, "solid", true);
  line(slide, x + 0.54, y + 0.40, x + 0.65, y + 0.44, C.ink, 0.7);
  line(slide, x + 0.54, y + 0.45, x + 0.65, y + 0.49, C.ink, 0.7);
}

const slide = pptx.addSlide();
slide.background = { color: C.paper };

text(slide, "Schematic surgical workflows for hip-preserving ONFH reconstruction", 0.18, 0.12, 6.84, 0.22, {
  size: 9.2,
  bold: true,
});
text(slide, "Conceptual figure for manuscript use; not to scale", 0.18, 0.36, 6.84, 0.12, {
  size: 5.6,
  color: C.muted,
});

rect(slide, 0.18, 0.62, 6.84, 1.62, C.panel, C.grid, 0.4, true);
panelHeader(
  slide,
  "A",
  "PVIBGT",
  "vascularized iliac flap transfer without intentional hip dislocation",
  0.30,
  0.74,
  6.60,
  C.teal,
  C.tealLight,
);

rect(slide, 0.18, 2.50, 6.84, 1.62, C.panel, C.grid, 0.4, true);
panelHeader(
  slide,
  "B",
  "SHD-IBG",
  "surgical dislocation followed by cancellous impaction bone grafting",
  0.30,
  2.62,
  6.60,
  C.orange,
  C.orangeLight,
);

const x0 = 0.36;
const yA = 1.05;
const yB = 2.93;
const tw = 1.46;
const th = 1.00;
const gap = 0.18;
const xs = [x0, x0 + (tw + gap), x0 + 2 * (tw + gap), x0 + 3 * (tw + gap)];

const pv = [
  ["Iliac flap harvest", iconFlapHarvest],
  ["Pedicle-preserving transfer", iconPedicleTransfer],
  ["Debridement with reduced hip", iconDebrideReduced],
  ["Vascularized flap implantation", iconFlapImplant],
];
const shd = [
  ["Trochanteric osteotomy + graft harvest", iconTrochanterHarvest],
  ["Surgical hip dislocation", iconDislocation],
  ["Necrotic bone removal", iconDebrideDislocated],
  ["Impaction grafting + fixation", iconImpaction],
];

pv.forEach(([label, fn], i) => {
  tile(slide, i + 1, label, xs[i], yA, tw, th, C.teal, C.tealLight, fn);
  if (i < pv.length - 1) arrow(slide, xs[i] + tw + 0.03, yA + 0.50, xs[i + 1] - 0.04, yA + 0.50, C.teal);
});

shd.forEach(([label, fn], i) => {
  tile(slide, i + 1, label, xs[i], yB, tw, th, C.orange, C.orangeLight, fn);
  if (i < shd.length - 1) arrow(slide, xs[i] + tw + 0.03, yB + 0.50, xs[i + 1] - 0.04, yB + 0.50, C.orange);
});

rect(slide, 0.30, 4.25, 6.60, 0.24, C.paper, C.grid, 0.35, true);
text(
  slide,
  "Mechanistic distinction: PVIBGT emphasizes pedicle perfusion and structural iliac support; SHD-IBG emphasizes open exposure, lesion clearance and mechanically packed cancellous graft support.",
  0.40,
  4.30,
  6.40,
  0.08,
  { size: 5.4, color: C.muted, align: "center" },
);

pptx.writeFile({ fileName: path.join(OUT, "surgical_workflows_jar_style_editable.pptx") });
