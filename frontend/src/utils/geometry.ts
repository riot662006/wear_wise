export function scaleClampXYWH(
  bbox: [number, number, number, number],
  sx: number,
  sy: number,
  vw: number,
  vh: number
): [number, number, number, number] {
  let [x, y, w, h] = bbox;
  x = Math.round(x * sx);
  y = Math.round(y * sy);
  w = Math.round(w * sx);
  h = Math.round(h * sy);

  // Clamp to video frame
  x = Math.max(0, Math.min(x, vw - 1));
  y = Math.max(0, Math.min(y, vh - 1));
  if (x + w > vw) w = vw - x;
  if (y + h > vh) h = vh - y;

  w = Math.max(1, w);
  h = Math.max(1, h);
  return [x, y, w, h];
}
