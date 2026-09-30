// Adapted from VisualForce's task selection and paired playback controller.
(() => {
  const project = window.DSP_PROJECT;
  const tasks = {
    sweep: { title: 'Sweep Ball' },
    cola: { title: 'Pick Cola' },
    drawer: { title: 'Place Bottle & Close Drawer' },
    coffee: { title: 'Coffee Preparation' }
  };
  const byId = id => document.getElementById(id);
  const setText = (id, value) => { byId(id).textContent = value; };
  document.title = project.title;
  const prefix = document.createElement('span');
  prefix.textContent = `${project.shortTitle}: `;
  byId('project-title').replaceChildren(prefix, document.createElement('br'), document.createTextNode(project.subtitle));
  project.authors.forEach(author => {
    const span = document.createElement('span');
    const name = document.createElement(author.url ? 'a' : 'span');
    name.textContent = author.name;
    if (author.url) name.href = author.url;
    span.append(name);
    if (author.affiliations) {
      const sup = document.createElement('sup');
      sup.textContent = author.affiliations;
      span.append(sup);
    }
    byId('authors').append(span);
  });
  byId('authors').hidden = project.authors.length === 0;
  project.affiliations.forEach(affiliation => {
    const span = document.createElement('span');
    const sup = document.createElement('sup');
    sup.textContent = affiliation.id;
    span.append(sup, document.createTextNode(affiliation.name));
    byId('affiliations').append(span);
  });
  byId('affiliations').hidden = project.affiliations.length === 0;
  setText('author-note', project.authorNote);
  byId('author-note').hidden = !project.authorNote;
  ['paper', 'code', 'fullVideo'].forEach(key => {
    if (!project[key]) return;
    byId(`${key}-link`).href = project[key];
    byId(`${key}-link`).hidden = false;
  });
  if (project.teaser) {
    byId('teaser-video').src = project.teaser;
    byId('teaser-video').poster = project.teaserPoster;
    byId('teaser-download').href = project.teaser;
    byId('teaser-video').hidden = false;
    byId('teaser-poster').hidden = true;
  }
  Object.entries(tasks).forEach(([task, data]) => {
    const section = byId('task-template').content.firstElementChild.cloneNode(true);
    section.id = `task-${task}`;
    const title = section.querySelector('[data-role="title"]');
    title.id = `${task}-title`;
    title.textContent = data.title;
    section.setAttribute('aria-labelledby', title.id);
    section.querySelector('.playback-controls').setAttribute('aria-label', `${data.title} playback controls`);
    const status = section.querySelector('.playback-status');
    const media = project.videos[task] || {};
    const videos = [];
    section.querySelectorAll('[data-outcome]').forEach(card => {
      const outcome = card.dataset.outcome;
      const src = media[outcome];
      card.hidden = !src;
      if (!src) return;
      const video = card.querySelector('video');
      video.id = `${task}-${outcome}-video`;
      video.src = src;
      video.poster = `static/images/videos/${task}-${outcome}.jpg`;
      video.setAttribute('aria-label', `${data.title}: ${outcome === 'success' ? 'successful trial' : 'failure case'}`);
      card.querySelector('a').href = src;
      videos.push(video);
      video.addEventListener('error', () => { status.textContent = 'A video could not load.'; });
    });
    section.hidden = videos.length === 0;
    section.querySelector('.video-grid').classList.toggle('single-video', videos.length === 1);
    section.querySelector('.playback-row').hidden = videos.length !== 2;
    let requestId = 0;
    function pause() {
      requestId += 1;
      videos.forEach(video => video.pause());
      status.textContent = '';
    }
    async function playBoth(restart = false) {
      const id = ++requestId;
      status.textContent = 'Loading videos...';
      if (restart) videos.forEach(video => { video.currentTime = 0; });
      const outcomes = await Promise.allSettled(videos.map(video => video.play()));
      if (id !== requestId) return;
      if (outcomes.some(outcome => outcome.status === 'rejected')) {
        videos.forEach(video => video.pause());
        status.textContent = 'Playback could not start. Try the individual video controls.';
      } else {
        status.textContent = '';
      }
    }
    section.querySelector('[data-action="play"]').addEventListener('click', () => playBoth());
    section.querySelector('[data-action="pause"]').addEventListener('click', pause);
    section.querySelector('[data-action="replay"]').addEventListener('click', () => playBoth(true));
    byId('task-list').append(section);
  });
})();
