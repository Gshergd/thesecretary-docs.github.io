/* Keep the right-hand contents list aligned with the section being read. */
(() => {
  const nav = document.querySelector('.right-nav');
  if (!nav) return;
  const sections = [...nav.querySelectorAll('a[href^="#"]')].map(link => ({
    link, heading: document.getElementById(decodeURIComponent(link.hash.slice(1)))
  })).filter(item => item.heading);
  if (!sections.length) return;
  let active, pending = false;
  function update() {
    pending = false;
    const offset = window.matchMedia('(max-width: 760px)').matches ? 110 : 100;
    let current = sections[0];
    for (const section of sections) {
      if (section.heading.getBoundingClientRect().top <= offset) current = section;
    }
    if (window.scrollY > 0 && window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) {
      current = sections[sections.length - 1];
    }
    if (current === active) return;
    for (const section of sections) {
      const selected = section === current;
      section.link.classList.toggle('active', selected);
      if (selected) section.link.setAttribute('aria-current', 'location');
      else section.link.removeAttribute('aria-current');
    }
    active = current;
    // Scroll only the contents panel; never move the document while reading.
    const panel = nav.getBoundingClientRect(), item = current.link.getBoundingClientRect();
    if (item.top < panel.top + 12) nav.scrollTop -= panel.top + 12 - item.top;
    else if (item.bottom > panel.bottom - 12) nav.scrollTop += item.bottom - panel.bottom + 12;
  }
  function schedule() {
    if (!pending) { pending = true; requestAnimationFrame(update); }
  }
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', schedule);
  window.addEventListener('hashchange', schedule);
  window.addEventListener('load', schedule);
  update();
})();
