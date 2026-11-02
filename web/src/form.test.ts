import { describe, it, expect } from 'vitest';
import { draftFrom, switchUnits, materialize } from './form';
import type { Metadata } from './api';
import metadataSchema from '../../docs/web-openapi.json';

describe('typed decimal boundary', () => {
  it('keeps incomplete numbers distinct from a calculated number', () => {
    // The real metadata fixture is loaded through the API in browser tests;
    // unit definitions here are exact existing core conversion definitions.
    const meta = { conversion_factors: { KG_PER_LB: .45359237, KG_M3_PER_LB_YD3: .45359237 / .764554857984,
      MM_PER_IN: 25.4, MPA_PER_PSI: .00689475729, KG_M3_PER_PCF: 16.01846337, M3_PER_YD3: .764554857984 } } as unknown as Metadata;
    const template = { water_kg: 200, batch_volume_m3: null } as Metadata['defaults_b'];
    const draft = draftFrom(template);
    draft.water_kg = '-';
    expect(materialize(draft, template, 'evaluate', 'SI', meta).errors.water_kg).toBeTruthy();
    draft.water_kg = '200';
    const us = switchUnits(draft, 'evaluate', 'US', meta);
    const si = switchUnits(us, 'evaluate', 'SI', meta);
    expect(Number(si.water_kg)).toBeCloseTo(200, 12);
    expect(metadataSchema.openapi).toBeTruthy();
  });
});
