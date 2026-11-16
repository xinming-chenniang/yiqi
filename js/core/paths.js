/**
 * 站点相对路径前缀
 *
 * 页面不再只有「根目录」和「pages/ 一层」两种：归档页在 pages/archive/ 下。
 * 按当前 URL 的目录层数算 `../` 前缀，避免每多一层就要在各组件里加一个 if。
 *
 * 用法：sitePrefix() → ''（根目录页面）/ '../'（pages/）/ '../../'（pages/archive/）
 */

export function sitePrefix() {
  const segments = window.location.pathname.split('/').filter(Boolean);
  // 最后一段是文件名（index.html 也算），目录层数 = 段数 - 1；站点挂在子路径下也能算对
  const depth = Math.max(0, segments.length - 1);
  return '../'.repeat(depth);
}
