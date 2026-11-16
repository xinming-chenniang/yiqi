/**
 * 页头组件
 *
 * 资源路径按当前页面的目录层数算（js/core/paths.js），归档页在 pages/archive/ 下也成立。
 */

import { sitePrefix } from '../core/paths.js';

export function loadHeader() {
  const logoPath = `${sitePrefix()}img/header-logo.webp`;

  const headerHTML = `
      <div class="header-content">
        <div class="header-logo">
          <img src="${logoPath}" alt="公会标志" class="logo-image" width="465" height="600">
        </div>
        <div class="header-text">
          <h1 class="guild-title">一起公会</h1>
          <p class="guild-motto">打本 休闲 洗脚</p>
        </div>
      </div>
    `;

  const headerContainer = document.querySelector('.guild-header-container');
  if (headerContainer) {
    headerContainer.innerHTML = headerHTML;
  }
}
