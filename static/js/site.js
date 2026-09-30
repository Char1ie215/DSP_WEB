'use strict';
const tasks = {
  sweep: { name: 'Sweep Ball', description: 'A Franka robot lifts a ball with a scoop and deposits it into a basket.', captions: ['Approach the ball', 'Reposition the scoop', 'Deposit the ball'] },
  cola: { name: 'Pick Cola', description: 'A Franka robot places a cola can onto a designated plate after a manual perturbation.', captions: ['Approach the can', 'External perturbation', 'Place the can'] },
  drawer: { name: 'Place Bottle & Close Drawer', description: 'A Franka robot places a bottle inside a drawer and closes the drawer.', captions: ['Approach the bottle', 'External perturbation', 'Close the drawer'] },
  coffee: { name: 'Coffee Preparation', description: 'A Franka and an ARX robot perform complementary subtasks, with interaction-induced deviations during execution.', captions: ['Prepare the milk', 'Interaction-induced deviation', 'Add coffee powder'] }
};
const tabs = [...document.querySelectorAll('[data-task]')];
function selectTask(tab) {
  const key = tab.dataset.task;
  const task = tasks[key];
  tabs.forEach(item => {
    item.setAttribute('aria-selected', String(item === tab));
    item.tabIndex = item === tab ? 0 : -1;
  });
  document.querySelector('#task-panel').setAttribute('aria-labelledby', tab.id);
  document.querySelector('#task-description').textContent = task.description;
  ['before', 'disturbance', 'after'].forEach((stage, index) => {
    const frame = document.querySelector(`#frame-${stage}`);
    frame.src = `static/images/${key}-${stage}.png`;
    frame.alt = `${task.name}: ${task.captions[index]}`;
    document.querySelector(`#caption-${stage}`).textContent = task.captions[index];
  });
}
tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => selectTask(tab));
  tab.addEventListener('keydown', event => {
    let next;
    if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
    if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = tabs.length - 1;
    if (next !== undefined) { event.preventDefault(); selectTask(tabs[next]); tabs[next].focus(); }
  });
});
