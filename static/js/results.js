// Transcribed from ICRA2027_DSP.pdf, Tables I-IV, pages 5-6.
// Strings preserve the manuscript's reported precision and trial-count format.
window.DSP_RESULTS = {
  methods: ['Raw Action', 'Action BSP', 'Ours (RAW)', 'Ours (BSP)'],
  simulation: [
    { id: 'libero', title: 'LIBERO-10', rows: [
      ['29.52', '9.28', '20.63'], ['27.96', '12.16', '20.61'],
      ['54.16', '49.64', '20.22'], ['45.56', '46.08', '20.25']
    ] },
    { id: 'lift', title: 'RoboMimic Lift', rows: [
      ['100.0', '14.8', '21.64'], ['100.0', '14.0', '21.61'],
      ['100.0', '69.6', '20.27'], ['99.6', '71.6', '20.24']
    ] },
    { id: 'square', title: 'MimicGen Square', rows: [
      ['49.2', '11.6', '21.61'], ['49.2', '8.4', '21.31'],
      ['59.6', '37.2', '19.39'], ['30.0', '37.2', '19.50']
    ] }
  ],
  realWorld: {
    cola: { table: 'III', rows: [['8/10', '2/10'], ['9/10', '2/10'], ['10/10', '6/10'], ['10/10', '8/10']] },
    drawer: { table: 'III', rows: [['7/10', '0/10'], ['4/10', '0/10'], ['9/10', '8/10'], ['5/10', '7/10']] },
    sweep: { table: 'III', rows: [['9/10', '0/10'], ['8/10', '0/10'], ['10/10', '7/10'], ['10/10', '9/10']] },
    coffee: { table: 'IV', methods: ['Raw Action', 'Ours (RAW)'], rows: [['4/10'], ['8/10']] }
  },
  recovery: {
    methods: ['Direct execution', 'Immediate replanning', 'Recover, then replan'],
    rows: [['11.84'], ['9.80'], ['49.64']]
  },
  scaling: {
    methods: ['1 candidate per query', '16 candidates per query'],
    rows: [['36.72'], ['45.56']]
  }
};

// One native table renderer keeps captions, headers, and reported values aligned.
window.renderResultsTable = (container, { id, caption, headers, methods, rows, scoreColumns }) => {
  const table = document.createElement('table');
  table.id = id;
  table.className = 'results-table data-table';
  const title = table.createCaption();
  title.textContent = caption;
  const head = table.createTHead().insertRow();
  headers.forEach(text => {
    const cell = document.createElement('th');
    cell.scope = 'col';
    cell.textContent = text;
    head.append(cell);
  });
  const maxima = scoreColumns.map(column => Math.max(...rows.map(row => parseFloat(row[column]))));
  const body = table.createTBody();
  rows.forEach((values, index) => {
    const row = body.insertRow();
    const label = document.createElement('th');
    label.scope = 'row';
    label.textContent = methods[index];
    row.append(label);
    values.forEach((value, column) => {
      const cell = row.insertCell();
      const scoreIndex = scoreColumns.indexOf(column);
      if (scoreIndex >= 0 && parseFloat(value) === maxima[scoreIndex]) {
        const strong = document.createElement('strong');
        strong.textContent = value;
        cell.append(strong);
      } else {
        cell.textContent = value;
      }
    });
  });
  container.append(table);
};
