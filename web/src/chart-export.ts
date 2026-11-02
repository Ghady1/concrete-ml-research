import { download } from './api';

export function tableCSV(rows: Record<string, unknown>[]): string {
  const keys = [...new Set(rows.flatMap(row => Object.keys(row)))];
  const cell = (value: unknown) => '"' + String(value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : value).replaceAll('"', '""') + '"';
  return [keys.map(cell).join(','), ...rows.map(row => keys.map(key => cell(row[key])).join(','))].join('\r\n');
}

/** Export the actual rendered figure with method context, not a recreated chart. */
export function figureSVG(source: SVGElement, title: string, note: string): { text: string; width: number; height: number } {
  const ns = 'http://www.w3.org/2000/svg';
  const width = Math.max(1, source.getBoundingClientRect().width);
  const chartHeight = Math.max(1, source.getBoundingClientRect().height);
  const limit = Math.max(25, Math.floor(width / 7));
  const lines: string[] = [];
  for (const text of [title, note + ' Research output; not a certified structural design value.']) {
    let line = '';
    for (const word of text.split(' ')) {
      if (line && line.length + word.length > limit) { lines.push(line); line = ''; }
      line += (line ? ' ' : '') + word;
    }
    if (line) lines.push(line);
  }
  const header = 25 + lines.length * 20;
  const height = chartHeight + header + 12;
  const root = document.createElementNS(ns, 'svg');
  root.setAttribute('xmlns', ns); root.setAttribute('width', String(width)); root.setAttribute('height', String(height));
  root.setAttribute('viewBox', `0 0 ${width} ${height}`);
  root.setAttribute('style', 'background:#fffefb;font-family:Arial,sans-serif;font-size:12px');
  const background = document.createElementNS(ns, 'rect');
  background.setAttribute('width', '100%'); background.setAttribute('height', '100%'); background.setAttribute('fill', '#fffefb'); root.append(background);
  const description = document.createElementNS(ns, 'desc');
  description.textContent = title + '. ' + note + ' Research prediction; not a certified structural design value.'; root.append(description);
  lines.forEach((line, index) => {
    const text = document.createElementNS(ns, 'text'); text.setAttribute('x', '10'); text.setAttribute('y', String(22 + index * 20));
    text.setAttribute('fill', '#25332f'); text.setAttribute('font-size', index === 0 ? '15' : '12'); text.textContent = line; root.append(text);
  });
  const chart = source.cloneNode(true) as SVGElement;
  chart.setAttribute('x', '0'); chart.setAttribute('y', String(header)); chart.setAttribute('width', String(width)); chart.setAttribute('height', String(chartHeight));
  root.append(chart);
  return { text: new XMLSerializer().serializeToString(root), width, height };
}

export async function saveFigure(source: SVGElement, title: string, note: string, format: 'svg' | 'png') {
  const file = title.toLowerCase().replaceAll(/[^a-z0-9]+/g, '-');
  const figure = figureSVG(source, title, note);
  if (format === 'svg') { download(file + '.svg', figure.text, 'image/svg+xml'); return; }
  const url = URL.createObjectURL(new Blob([figure.text], { type: 'image/svg+xml' }));
  try {
    const image = new Image();
    await new Promise<void>((resolve, reject) => { image.onload = () => resolve(); image.onerror = () => reject(new Error('The browser could not render this chart image. Download SVG instead.')); image.src = url; });
    const canvas = document.createElement('canvas'); canvas.width = Math.ceil(figure.width * 3); canvas.height = Math.ceil(figure.height * 3);
    const context = canvas.getContext('2d'); if (!context) throw new Error('Image export is unavailable in this browser.');
    context.scale(3, 3); context.drawImage(image, 0, 0);
    const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('Image export failed.')), 'image/png'));
    download(file + '.png', blob);
  } finally { URL.revokeObjectURL(url); }
}
