/**
 * 首页顶部天梯（标签切换）
 *
 * 6 份天梯数据全在 js/data/ 下，由 tools/fetch_tier_lists.py 每周生成；
 * 总览页 pages/all-rankings.html 仍然六份并列展示。
 */

import dpsTierList from '../data/dps-tier-list.js';
import healerTierList from '../data/healer-tier-list.js';
import tankTierList from '../data/tank-tier-list.js';
import mplusDpsTierList from '../data/mplus-dps-tier-list.js';
import mplusHealerTierList from '../data/mplus-healer-tier-list.js';
import mplusTankTierList from '../data/mplus-tank-tier-list.js';

import { TierListTabs } from '../components/TierListTabs.js';

const TABS = [
  { key: 'mplus-dps', label: '大秘境 DPS', icon: 'sword', type: 'dps', data: mplusDpsTierList },
  {
    key: 'mplus-healer',
    label: '大秘境治疗',
    icon: 'heart',
    type: 'healer',
    data: mplusHealerTierList
  },
  { key: 'mplus-tank', label: '大秘境坦克', icon: 'shield', type: 'tank', data: mplusTankTierList },
  { key: 'raid-dps', label: '团本 DPS', icon: 'sword', type: 'dps', data: dpsTierList },
  { key: 'raid-healer', label: '团本治疗', icon: 'heart', type: 'healer', data: healerTierList },
  { key: 'raid-tank', label: '团本坦克', icon: 'shield', type: 'tank', data: tankTierList }
];

function init() {
  new TierListTabs('home-tier-tabs', TABS, 'mplus-dps');
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
