/**
 * nav.js — Injects a shared navbar into any page.
 * Call initNav() after DOMContentLoaded.
 */
function initNav() {
  if (document.getElementById('main-nav')) return;
  const user = typeof getCurrentUser === 'function' ? getCurrentUser() : null;
  const currentPage = location.pathname.split('/').pop() || 'index.html';
  const isActive = (page) => currentPage === page ? ' nav__link--active' : '';
  const navHTML = `
    <nav class="nav" id="main-nav" role="navigation" aria-label="Main navigation">
      <div class="nav__inner">
        <a href="index.html" class="nav__brand" aria-label="HCP Home">
          <svg class="nav__brand-icon" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path d="M16 28 C10 22 4 18 4 11 C4 7 8 4 12 5 C14 5.5 15.5 6.5 16 8 C16.5 6.5 18 5.5 20 5 C24 4 28 7 28 11 C28 18 22 22 16 28Z" fill="currentColor" opacity="0.85"/>
            <path d="M16 15 L16 28" stroke="white" stroke-width="1.5" stroke-linecap="round" opacity="0.6"/>
            <path d="M16 18 L12 15" stroke="white" stroke-width="1.2" stroke-linecap="round" opacity="0.5"/>
            <path d="M16 21 L20 18" stroke="white" stroke-width="1.2" stroke-linecap="round" opacity="0.5"/>
          </svg>
          <span class="nav__brand-name">CrossWise</span>
        </a>
        <button class="nav__hamburger" id="nav-hamburger" aria-label="Toggle menu" aria-expanded="false">
          <span></span><span></span><span></span>
        </button>
        <div class="nav__links" id="nav-links" role="menubar">
          <a href="index.html" class="nav__link${isActive('index.html')}" role="menuitem">Home</a>
          <a href="about.html" class="nav__link${isActive('about.html')}" role="menuitem">About</a>
          ${user
            ? `<a href="upload.html" class="nav__link${isActive('upload.html')}" role="menuitem">Virtual Breeding</a>
               <a href="dashboard.html" class="nav__link${isActive('dashboard.html')}" role="menuitem">Dashboard</a>
               ${user.is_admin ? `<a href="admin.html" class="nav__link nav__link--admin${isActive('admin.html')}" role="menuitem"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>Admin</a>` : ''}`
            : ''
          }
        </div>
        <div class="nav__auth">
          ${user
            ? `<span class="nav__user">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                  <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="1.8"/>
                </svg>
                ${user.name.split(' ')[0]}
               </span>
               <button class="btn btn--nav-outline" onclick="logoutUser()">Sign out</button>`
            : `<a href="login.html" class="nav__link${isActive('login.html')}">Sign in</a>
               <a href="register.html" class="btn btn--nav-filled${isActive('register.html')}">Get started</a>`
          }
        </div>
      </div>
    </nav>
  `;
  // Insert before first child of body
  document.body.insertAdjacentHTML('afterbegin', navHTML);
  // Inject Admin link into footer if user is admin
  if (user && user.is_admin) {
    // Wait a tick for the footer to be parsed if it's below the script tag
    setTimeout(() => {
      const footerVersion = document.getElementById('footer-version');
      if (footerVersion) {
        footerVersion.insertAdjacentHTML('afterend', '&nbsp;·&nbsp; <a href="admin.html" style="color: var(--faint);">Admin Portal</a> ');
      }
    }, 0);
  }
  // Mobile hamburger toggle
  const ham = document.getElementById('nav-hamburger');
  if (ham) {
    ham.addEventListener('click', function () {
      const links = document.getElementById('nav-links');
      const open = links.classList.toggle('nav__links--open');
      this.setAttribute('aria-expanded', open);
      this.classList.toggle('nav__hamburger--open', open);
    });
  }
  // Scroll behaviour — shrink nav on scroll
  window.addEventListener('scroll', () => {
    const nav = document.getElementById('main-nav');
    if (nav) nav.classList.toggle('nav--scrolled', window.scrollY > 40);
  }, { passive: true });
}
document.addEventListener('DOMContentLoaded', initNav);
