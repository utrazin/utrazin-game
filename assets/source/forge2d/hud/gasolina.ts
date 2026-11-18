import { defineAsset } from '@core';
import { PALETTES } from '../_theme';

// Icone de gasolina do HUD (galao). Teste de integracao do Forge 2D.
export default defineAsset({
  width: 64,
  height: 64,
  scale: 2,
  render({ ctx }) {
    const body = new Path2D();
    body.roundRect(16, 20, 32, 38, 5);
    ctx.fillStyle = '#b8261d';
    ctx.fill(body);
    ctx.lineWidth = 3; ctx.strokeStyle = PALETTES.ink; ctx.stroke(body);
    // alca
    ctx.beginPath(); ctx.roundRect(22, 8, 16, 12, 3); ctx.lineWidth = 4; ctx.stroke();
    // bico
    ctx.fillStyle = PALETTES.accent; ctx.fillRect(40, 12, 7, 9); ctx.lineWidth = 2; ctx.strokeRect(40, 12, 7, 9);
    // X em relevo
    ctx.strokeStyle = '#7a1712'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(22, 28); ctx.lineTo(42, 50); ctx.moveTo(42, 28); ctx.lineTo(22, 50); ctx.stroke();
  },
});
