/**
 * 顶部导航
 *
 * 桌面端：横向排列，下拉菜单支持 hover 与点击/键盘展开。
 * 移动端（≤768px）：折叠为「菜单」按钮，展开后纵向排列，下拉改为手风琴。
 */

import { sitePrefix } from '../core/paths.js';

const MENU_MEDIA_QUERY = '(min-width: 769px)';

export function loadNavigation() {
  const prefix = sitePrefix();

  const homePath = `${prefix}index.html`;
  const pagesPath = `${prefix}pages/`;
  const imgPath = `${prefix}img/nav/wcl.png`;

  const navHTML = `
    <button type="button" class="nav-toggle" aria-expanded="false" aria-controls="primary-nav" aria-label="打开菜单">
      <span class="nav-toggle-icon" aria-hidden="true">☰</span>
      <span class="nav-toggle-label">菜单</span>
    </button>

    <ul id="primary-nav">
      <li><a href="${homePath}">首页</a></li>

      <li class="dropdown">
        <button type="button" class="dropbtn" aria-expanded="false" aria-controls="nav-menu-tools">
          实用网站 <span class="dropbtn-caret" aria-hidden="true">▼</span>
        </button>
        <div class="dropdown-content" id="nav-menu-tools">
          <a href="https://www.warcraftlogs.com/guild/rankings/586445/latest?difficulty=4" target="_blank" rel="noopener" class="dropdown-item">
            <span class="dropdown-icon">
              <img src="${imgPath}" alt="" width="24" height="24">
            </span>
            <div class="dropdown-text">
              <span class="dropdown-title">Warcraft Logs</span>
              <span class="dropdown-desc">战斗数据分析与排行</span>
            </div>
          </a>
          <a href="https://raider.io" target="_blank" rel="noopener" class="dropdown-item">
            <span class="dropdown-icon">
              <img src="https://cdn.raiderio.net/images/mstile-144x144.png" alt="" width="24" height="24" loading="lazy">
            </span>
            <div class="dropdown-text">
              <span class="dropdown-title">Raider.IO</span>
              <span class="dropdown-desc">大秘境评分</span>
            </div>
          </a>
        </div>
      </li>

      <li class="dropdown">
        <button type="button" class="dropbtn" aria-expanded="false" aria-controls="nav-menu-raid">
          团本工具 <span class="dropbtn-caret" aria-hidden="true">▼</span>
        </button>
        <div class="dropdown-content" id="nav-menu-raid">
          <a href="https://raidplan.io/plan/create?raid=wow.undermine" target="_blank" rel="noopener" class="dropdown-item">
            <div class="dropdown-text">
              <span class="dropdown-title">RaidPlan</span>
              <span class="dropdown-desc">战术图绘制</span>
            </div>
          </a>
        </div>
      </li>

      <li><a href="${pagesPath}gallery.html">公会画廊</a></li>
      <li><a href="${pagesPath}all-rankings.html">职业排名</a></li>
      <li><a href="${pagesPath}wcl.html">开荒记录</a></li>
      <li><a href="${pagesPath}other.html">其他</a></li>
    </ul>
  `;

  const navContainer = document.querySelector('.nav-container');
  if (!navContainer) return;

  navContainer.innerHTML = navHTML;
  markActiveLink(navContainer);
  initNavigation(navContainer);
}

/** 给当前页面对应的导航项加高亮与 aria-current */
function markActiveLink(container) {
  const current = (window.location.pathname.split('/').pop() || 'index.html').toLowerCase();

  container.querySelectorAll('#primary-nav a[href]').forEach((link) => {
    const href = link.getAttribute('href') || '';
    const target = href.split('/').pop().split('?')[0].toLowerCase();
    if (!target || target !== current) return;

    link.classList.add('is-active');
    link.setAttribute('aria-current', 'page');

    const dropdown = link.closest('.dropdown');
    if (dropdown) {
      dropdown.querySelector('.dropbtn')?.classList.add('is-active');
    }
  });
}

function initNavigation(container) {
  const toggle = container.querySelector('.nav-toggle');
  const dropdownButtons = Array.from(container.querySelectorAll('.dropbtn'));

  const setToggleState = (open) => {
    if (!toggle) return;
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? '关闭菜单' : '打开菜单');
    const icon = toggle.querySelector('.nav-toggle-icon');
    if (icon) icon.textContent = open ? '✕' : '☰';
  };

  const closeDropdowns = (except = null) => {
    dropdownButtons.forEach((button) => {
      if (button === except) return;
      button.setAttribute('aria-expanded', 'false');
      button.closest('.dropdown')?.classList.remove('open');
    });
  };

  const closeMenu = () => {
    container.classList.remove('nav-open');
    setToggleState(false);
    closeDropdowns();
  };

  toggle?.addEventListener('click', () => {
    const open = container.classList.toggle('nav-open');
    setToggleState(open);
    if (!open) closeDropdowns();
  });

  dropdownButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const item = button.closest('.dropdown');
      const open = item.classList.toggle('open');
      button.setAttribute('aria-expanded', String(open));
      closeDropdowns(button);
    });
  });

  // Esc：先收下拉，再收整个菜单，并把焦点还回去
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;

    const openItem = container.querySelector('.dropdown.open');
    if (openItem) {
      const button = openItem.querySelector('.dropbtn');
      openItem.classList.remove('open');
      button?.setAttribute('aria-expanded', 'false');
      button?.focus();
      return;
    }

    if (container.classList.contains('nav-open')) {
      closeMenu();
      toggle?.focus();
    }
  });

  // 点击菜单外部收起
  document.addEventListener('click', (event) => {
    if (container.contains(event.target)) return;
    closeDropdowns();
    if (container.classList.contains('nav-open')) closeMenu();
  });

  // 从移动端切回桌面时复位，避免状态残留
  window.matchMedia(MENU_MEDIA_QUERY).addEventListener('change', (event) => {
    if (event.matches) {
      closeMenu();
    }
  });
}
