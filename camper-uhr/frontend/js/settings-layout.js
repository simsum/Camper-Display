// Reparent existing controls without replacing them or their event handlers.
(() => {
  const groups = [
    ['modules', 'Module & Reihenfolge', 'Stand, Fahrt und Anzeigedauer', ['section-modules']],
    ['photos', 'Reisemomente', 'Fotos verwalten und manuell anzeigen', ['section-photos']],
    ['display', 'Anzeige & Nachtmodus', 'Farben, Helligkeit und Zeitplan', ['section-display','section-colors','section-night']],
    ['vacation', 'Urlaub & Ankunft', 'Reisen, iCloud-Kalender und Begrüßung', ['section-vacations','section-calendar','section-arrival']],
    ['map', 'Karte & Wetter', 'Zoom, Fahrspur und Temperatureinheit', ['section-map','section-weather']],
    ['connections', 'Verbindungen', 'GPS-Router und Traccar', ['section-gps','traccar-settings']],
    ['tests', 'Erweitert & Tests', 'Simulation und Ankunft testen', ['section-simulation']],
  ];
  const main = document.createElement('main');
  main.id = 'settings-groups';
  document.querySelector('.save-bar').before(main);
  for (const [id,title,description,items] of groups) {
    const details = document.createElement('details');
    details.id = `group-${id}`;
    details.className = 'settings-group';
    const summary = document.createElement('summary');
    const heading = document.createElement('strong');heading.textContent=title;
    const hint = document.createElement('span');hint.textContent=description;
    summary.append(heading,hint);details.append(summary);
    for (const item of items) details.append(document.getElementById(item));
    main.append(details);
  }
  const tests = document.createElement('fieldset');
  const legend = document.createElement('legend');legend.textContent='Ankunft testen';
  tests.append(legend,document.getElementById('arrival-test'),document.getElementById('arrival-test-status'));
  document.getElementById('group-tests').append(tests);
  // Summary must be the first child for native keyboard/accessibility behavior.
  const testGroup=document.getElementById('group-tests');
  testGroup.prepend(testGroup.querySelector('summary'));
})();
