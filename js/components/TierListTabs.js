/**
 * 天梯标签切换（首页顶部用）
 *
 * 6 份天梯在同一张卡片里用标签切换，一次只渲染当前选中的那份 ——
 * 全都铺开会让首页首屏塞进六份排名。数据与页面结构见 js/data/*-tier-list.js /
 * pages/all-rankings.html（总览页仍然是六份并列）。
 *
 * 样式见 css/tier-list.css 的 .tier-tabs；键盘左右方向键可切换标签。
 */

import { TierList } from './TierList.js';
import { icon } from '../core/icons.js';

export class TierListTabs {
  /**
   * @param {string} containerId 承载标签栏的容器 id
   * @param {Array<{key: string, label: string, icon: string, type: 'dps'|'healer'|'tank', data: object}>} tabs
   * @param {string} defaultKey 默认选中的标签
   */
  constructor(containerId, tabs, defaultKey) {
    this.container = document.getElementById(containerId);
    this.tabs = tabs;
    this.activeKey = tabs.some((tab) => tab.key === defaultKey) ? defaultKey : tabs[0]?.key;
    this.panelId = `${containerId}-panel`;
    this.slotId = `${this.panelId}-slot`;
    this.init();
  }

  init() {
    if (!this.container || this.tabs.length === 0) return;
    this.render();
    this.addEventListeners();
    this.select(this.activeKey);
  }

  render() {
    this.container.innerHTML = `
      <div class="tier-tabs" role="tablist" aria-label="选择天梯">
        ${this.tabs.map((tab) => this.renderTab(tab)).join('')}
      </div>
      <div class="tier-tab-panel" id="${this.panelId}" role="tabpanel">
        <div id="${this.slotId}"></div>
      </div>
    `;
    this.tablist = this.container.querySelector('.tier-tabs');
    this.panel = this.container.querySelector('.tier-tab-panel');
    this.slot = this.container.querySelector(`#${this.slotId}`);
  }

  renderTab(tab) {
    const selected = tab.key === this.activeKey;
    return `
      <button type="button"
              class="tier-tab${selected ? ' is-active' : ''}"
              role="tab"
              id="tier-tab-${tab.key}"
              data-key="${tab.key}"
              aria-selected="${selected}"
              aria-controls="${this.panelId}"
              tabindex="${selected ? '0' : '-1'}">
        ${icon(tab.icon)} ${tab.label}
      </button>
    `;
  }

  addEventListeners() {
    this.tablist.querySelectorAll('.tier-tab').forEach((button) => {
      button.addEventListener('click', () => this.select(button.getAttribute('data-key')));
    });

    this.tablist.addEventListener('keydown', (event) => {
      const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
      if (step === 0) return;
      event.preventDefault();
      const index = this.tabs.findIndex((tab) => tab.key === this.activeKey);
      const next = (index + step + this.tabs.length) % this.tabs.length;
      this.select(this.tabs[next].key);
    });
  }

  select(key) {
    const tab = this.tabs.find((item) => item.key === key);
    if (!tab) return;
    // 已经渲染过同一份就不用重建（点击当前标签不该重播入场动画）
    if (key === this.activeKey && this.renderedKey === key) return;

    this.activeKey = key;
    this.tablist.querySelectorAll('.tier-tab').forEach((button) => {
      const selected = button.getAttribute('data-key') === key;
      button.classList.toggle('is-active', selected);
      button.setAttribute('aria-selected', String(selected));
      button.setAttribute('tabindex', selected ? '0' : '-1');
      if (selected) button.focus({ preventScroll: true });
    });

    this.panel.setAttribute('aria-labelledby', `tier-tab-${key}`);
    this.slot.innerHTML = '';
    this.renderedKey = key;
    // TierList 按容器 id 挂载；清空后重建，切回来时用当前数据重新渲染
    new TierList(this.slotId, tab.data, tab.type);
  }
}
