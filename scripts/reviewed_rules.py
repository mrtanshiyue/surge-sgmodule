"""Narrow upstream rules whose current matches overwrite unrelated data."""

PDD = r'^https?:\/\/mobile\.yangkeduo\.com\/proxy\/api\/api\/express\/post\/waybill\/red_packet\/goods_list$'
XIMA = r'^https:\/\/(mobile|mobilehera|mobwsa)\.ximalaya\.com\/discovery-feed\/v\d\/mix\/'
PDD_FILTER = ('reduce [["list"], ["data","list"], ["result","list"]][] as $p '
              '(. ; if ((try getpath($p) catch null) | type) == "array" '
              'then setpath($p; []) else . end)')
XIMA_FILTER = ('if (try .heData catch null | type) == "array" then .heData |= map('
               'if ((try .item.list catch null) | type) == "array" and '
               'any(.item.list[]?; (try .bizType catch null) == "SceneListenCard") '
               'then .item.list |= map(select((try .bizType catch null) != "SceneListenCard")) '
               '| select(.item.list != []) else . end) else . end')
VOLC_REJECT = ('AND,((NOT,((DOMAIN,volcengine-kdocs-cache.wpscdn.cn))),'
               '(NOT,((DOMAIN,vod-settings.volcvod.com))),'
               '(NOT,((DOMAIN,volcengine-kdocs-cache.wpscdn.cn))),'
               '(OR,((DOMAIN-KEYWORD,volc)))),REJECT')


def narrow_rule(section, line):
    if section == 'Rule' and line == VOLC_REJECT:
        return None
    if section == 'Body Rewrite':
        if line == f'http-response {PDD} ' + r'"list":\[.+\] "list":[]':
            return f"http-response-jq {PDD} '{PDD_FILTER}'"
        if line == f"http-response-jq {XIMA} " + """'.heData |= map(select(.item.list[].bizType != "SceneListenCard"))'""":
            return f"http-response-jq {XIMA} '{XIMA_FILTER}'"
    if section == 'Map Local':
        line = line.replace(r'wmapi\.meituan\.com\/api\/v7\/(loadInfo|openscreen|startpicture)',
                            r'wmapi\.meituan\.com\/api\/v7\/(openscreen|startpicture)')
        line = line.replace(r'.+\.googleapis.com/', r'[A-Za-z0-9.-]+\.googleapis\.com/')
        if r'\.music\.163.com\/' in line:
            line = '^' + line.lstrip('^').replace(r'\.music\.163.com\/', r'\.music\.163\.com\/')
    if section == 'Script' and '/Scripts/jingdong/jingdong.js' in line:
        line = line.replace(r'functionId=(deliverLayer|getTabHomeInfo|myOrderInfo|orderTrackBusiness|personinfoBusiness|start|welcomeHome),',
                            r'functionId=(deliverLayer|getTabHomeInfo|myOrderInfo|orderTrackBusiness|personinfoBusiness|start|welcomeHome)(?:&|$),')
    return line
