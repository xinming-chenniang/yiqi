/**
 * 团本坦克天梯（排名数据）
 *
 * 专精图标与职业信息统一见 specs.js，此处只保留层级与元数据。
 * 来源: https://www.wowhead.com/cn/guide/classes/tier-lists/tank-rankings-raids
 * 更新: 2026/10/26
 *
 * 由 tools/fetch_tier_lists.py 自动生成，请勿手改。
 */

const tankTierList = {
  "title": "Tank Raid Rankings for Midnight Season 2 - Best Specs",
  "source": "Dratnos",
  "lastUpdated": "2026/10/26",
  "fetchedAt": "2026/10/26",
  "sourceUrl": "https://www.wowhead.com/cn/guide/classes/tier-lists/tank-rankings-raids",
  "tiers": {
    "S": {
      "name": "S",
      "description": "",
      "specs": [
        "death-knight|鲜血"
      ]
    },
    "A+": {
      "name": "A+",
      "description": "",
      "specs": []
    },
    "A": {
      "name": "A",
      "description": "",
      "specs": [
        "paladin|防护",
        "druid|守护"
      ]
    },
    "B": {
      "name": "B",
      "description": "",
      "specs": [
        "demon-hunter|复仇",
        "monk|酒仙",
        "warrior|防护"
      ]
    },
    "C": {
      "name": "C",
      "description": "",
      "specs": []
    },
    "D": {
      "name": "D",
      "description": "",
      "specs": []
    },
    "F": {
      "name": "F",
      "description": "",
      "specs": []
    }
  }
};

export default tankTierList;
