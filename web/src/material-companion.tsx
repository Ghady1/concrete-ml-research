export type MaterialKind = 'cement' | 'coarse' | 'fine' | 'water';

/** Original decorative vectors: no material properties or analysis state implied. */
export function MaterialCompanion({ material, reaction = 0, rounded = false }: { material: MaterialKind; reaction?: number; rounded?: boolean }) {
  const color = { cement: '#c6c7b8', coarse: '#a7b6a0', fine: '#dfbd87', water: '#8ac6cc' }[material];
  const ink = '#354c46';
  return <span className={'material-companion companion-' + material} aria-hidden="true">
    <svg viewBox="0 0 144 138" focusable="false">
      <ellipse cx="74" cy="126" rx="39" ry="5" fill="#354c46" opacity=".08"/>
      <g key={reaction} className="companion-body" stroke={ink} strokeWidth="2.3" strokeLinejoin="round" strokeLinecap="round">
        <path d="M48 103Q46 119 36 120Q31 129 45 127L59 118M87 108Q88 121 100 120Q110 127 99 128L83 123" fill={color}/>
        <path d="M39 70Q22 75 27 88Q30 94 34 87M106 72Q121 77 118 88" fill="none"/>
        {material === 'cement' && <>
          <path d="M44 31L99 28L107 98Q106 113 76 114Q42 114 37 101Z" fill={color}/>
          <path d="M44 31L40 21Q71 27 101 20L99 28M45 37L96 34" fill="#e7e5d7"/>
          <path d="M47 58L97 55L100 94L43 97Z" fill="#f7f3e8" strokeWidth="1.3"/>
          <path d="M56 43L67 42M85 103L97 101" opacity=".4"/>
        </>}
        {material === 'coarse' && <>
          {rounded ? <ellipse cx="73" cy="74" rx="39" ry="40" fill={color}/> : <path d="M35 74L44 43L68 32L98 40L111 68L103 103L74 114L44 103Z" fill={color}/>}
          {!rounded && <path d="M44 43L61 58L68 32M61 58L35 74M98 40L88 57L111 68M103 103L87 94L74 114" fill="none" opacity=".38"/>}
          <path d="M48 95L55 99M96 72L100 79" opacity=".35"/>
        </>}
        {material === 'fine' && <>
          <path d="M35 100Q36 82 48 74Q53 66 54 52Q57 36 71 34Q87 36 89 54Q91 69 100 77Q113 89 109 103Q78 120 35 100Z" fill={color}/>
          <path d="M57 49Q62 42 67 43M43 96L47 94M94 96L98 98" fill="none" opacity=".5"/>
          {[ [58,60], [84,61], [47,84], [101,88], [62,102], [81,105], [75,47] ].map(([cx,cy], i) => <circle key={i} cx={cx} cy={cy} r="1.2" stroke="none" fill="#a9814e"/>)}
        </>}
        {material === 'water' && <>
          <path d="M73 17C69 34 36 59 36 82A37 32 0 0 0 110 82C110 59 81 37 73 17Z" fill={color}/>
          <path d="M49 70Q47 78 49 82" fill="none" stroke="#f5ffff" strokeWidth="5"/>
        </>}
        <g className="companion-face">
          <path d="M59 77V81M84 77V81" fill="none" strokeWidth="4"/>
          <path d="M67 88Q72 94 78 88" fill="none" strokeWidth="2"/>
          <ellipse cx="52" cy="87" rx="5" ry="2.8" fill="#c17c69" stroke="none" opacity=".45"/>
          <ellipse cx="92" cy="87" rx="5" ry="2.8" fill="#c17c69" stroke="none" opacity=".45"/>
        </g>
      </g>
    </svg>
  </span>;
}
