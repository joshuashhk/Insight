"""
JSON生成模块

将API返回的原始数据转换为结构化JSON，保留中文字段名和格式化数值。
支持不同类型公司的财务报表：非金融、银行、保险、证券、其它金融。
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


def _fmt_amount(value) -> Optional[float]:
    """金额转亿元，保留2位小数"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(value / 1e8, 2)
    return value


def _fmt_pct(value) -> Optional[float]:
    """比例转百分比，保留2位小数"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(value * 100, 2)
    return value


def _fmt_date(value) -> Optional[str]:
    """日期去掉时间部分"""
    if value is None:
        return None
    if isinstance(value, str) and "T" in value:
        return value.split("T")[0]
    return str(value)


def _get_field(record: dict, table: str, field: str) -> Any:
    """从API记录中提取字段值"""
    return record.get("q", {}).get(table, {}).get(field, {}).get("t")


def fields_to_metrics(fields: List[Tuple]) -> List[str]:
    """将字段映射转换为API指标列表"""
    return [f"q.{table}.{field}.t" for _, (table, field), _ in fields]


# ==================== 非金融企业字段 ====================

BALANCE_SHEET_FIELDS: List[Tuple[str, Tuple[str, str], str]] = [
    # 资产
    ("总资产", ("bs", "ta"), "amount"),
    ("流动资产合计", ("bs", "tca"), "amount"),
    ("货币资金", ("bs", "cabb"), "amount"),
    ("交易性金融资产", ("bs", "tfa"), "amount"),
    ("应收票据", ("bs", "nr"), "amount"),
    ("应收账款", ("bs", "ar"), "amount"),
    ("应收款项融资", ("bs", "rf"), "amount"),
    ("预付款项", ("bs", "ats"), "amount"),
    ("其他应收款", ("bs", "or"), "amount"),
    ("存货", ("bs", "i"), "amount"),
    ("合同资产", ("bs", "ca"), "amount"),
    ("一年内到期的非流动资产", ("bs", "ncadwioy"), "amount"),
    ("其他流动资产", ("bs", "oca"), "amount"),
    ("非流动资产合计", ("bs", "tnca"), "amount"),
    ("长期股权投资", ("bs", "ltei"), "amount"),
    ("其他权益工具投资", ("bs", "oeii"), "amount"),
    ("其他非流动金融资产", ("bs", "oncfa"), "amount"),
    ("投资性房地产", ("bs", "rei"), "amount"),
    ("固定资产", ("bs", "fa"), "amount"),
    ("在建工程", ("bs", "cip"), "amount"),
    ("使用权资产", ("bs", "roua"), "amount"),
    ("无形资产", ("bs", "ia"), "amount"),
    ("开发支出", ("bs", "rade"), "amount"),
    ("商誉", ("bs", "gw"), "amount"),
    ("长期待摊费用", ("bs", "ltpe"), "amount"),
    ("递延所得税资产", ("bs", "dita"), "amount"),
    ("其他非流动资产", ("bs", "onca"), "amount"),
    # 负债
    ("负债合计", ("bs", "tl"), "amount"),
    ("有息负债", ("bs", "lwi"), "amount"),
    ("流动负债合计", ("bs", "tcl"), "amount"),
    ("短期借款", ("bs", "stl"), "amount"),
    ("应付票据", ("bs", "np"), "amount"),
    ("应付账款", ("bs", "ap"), "amount"),
    ("合同负债", ("bs", "cl"), "amount"),
    ("应付职工薪酬", ("bs", "sawp"), "amount"),
    ("应交税费", ("bs", "tp"), "amount"),
    ("其他应付款", ("bs", "oap"), "amount"),
    ("一年内到期的非流动负债", ("bs", "ncldwioy"), "amount"),
    ("其他流动负债", ("bs", "ocl"), "amount"),
    ("非流动负债合计", ("bs", "tncl"), "amount"),
    ("长期借款", ("bs", "ltl"), "amount"),
    ("应付债券", ("bs", "bp"), "amount"),
    ("租赁负债", ("bs", "ll"), "amount"),
    ("长期应付款", ("bs", "ltap"), "amount"),
    ("递延所得税负债", ("bs", "ditl"), "amount"),
    # 所有者权益
    ("所有者权益合计", ("bs", "toe"), "amount"),
    ("股本", ("bs", "sc"), "amount"),
    ("资本公积", ("bs", "capr"), "amount"),
    ("库存股", ("bs", "is"), "amount"),
    ("其他综合收益", ("bs", "oci"), "amount"),
    ("盈余公积", ("bs", "surr"), "amount"),
    ("未分配利润", ("bs", "rtp"), "amount"),
    ("归属于母公司股东权益", ("bs", "tetoshopc"), "amount"),
    ("少数股东权益", ("bs", "etmsh"), "amount"),
    # 关键比率
    ("资产负债率", ("bs", "tl_ta_r"), "pct"),
    ("有息负债率", ("bs", "lwi_ta_r"), "pct"),
    ("流动比率", ("bs", "tca_tcl_r"), "ratio"),
    ("速动比率", ("bs", "q_r"), "ratio"),
    ("股东权益占比", ("bs", "toe_ta_r"), "pct"),
    ("固定资产占比", ("bs", "fa_ta_r"), "pct"),
    ("商誉占净资产比", ("bs", "gw_toe_r"), "pct"),
    ("净营运资本", ("bs", "nwc"), "amount"),
]

INCOME_STATEMENT_FIELDS: List[Tuple[str, Tuple[str, str], str]] = [
    # 营业收入
    ("营业总收入", ("ps", "toi"), "amount"),
    ("营业收入", ("ps", "oi"), "amount"),
    # 营业成本
    ("营业总成本", ("ps", "toc"), "amount"),
    ("营业成本", ("ps", "oc"), "amount"),
    ("毛利率", ("ps", "gp_m"), "pct"),
    ("税金及附加", ("ps", "tas"), "amount"),
    ("销售费用", ("ps", "se"), "amount"),
    ("管理费用", ("ps", "ae"), "amount"),
    ("研发费用", ("ps", "rade"), "amount"),
    ("财务费用", ("ps", "fe"), "amount"),
    ("利息费用", ("ps", "ieife"), "amount"),
    ("利息收入", ("ps", "iiife"), "amount"),
    # 其他收益
    ("其他收益", ("ps", "oic"), "amount"),
    ("投资收益", ("ps", "ivi"), "amount"),
    ("公允价值变动收益", ("ps", "ciofv"), "amount"),
    ("信用减值损失", ("ps", "cilor"), "amount"),
    ("资产减值损失", ("ps", "ailor"), "amount"),
    ("资产处置收益", ("ps", "adi"), "amount"),
    # 利润
    ("核心利润", ("ps", "cp"), "amount"),
    ("营业利润", ("ps", "op"), "amount"),
    ("营业外收入", ("ps", "noi"), "amount"),
    ("营业外支出", ("ps", "noe"), "amount"),
    ("利润总额", ("ps", "tp"), "amount"),
    ("所得税费用", ("ps", "ite"), "amount"),
    ("净利润", ("ps", "np"), "amount"),
    ("归属于母公司股东的净利润", ("ps", "npatoshopc"), "amount"),
    ("少数股东损益", ("ps", "npatmsh"), "amount"),
    ("扣非归母净利润", ("ps", "npadnrpatoshaopc"), "amount"),
    # 每股指标
    ("基本每股收益", ("ps", "beps"), "raw"),
    ("稀释每股收益", ("ps", "deps"), "raw"),
    # 综合收益
    ("综合收益总额", ("ps", "tci"), "amount"),
    # 盈利能力指标
    ("净利率", ("ps", "np_s_r"), "pct"),
    ("营业利润率", ("ps", "op_s_r"), "pct"),
    ("核心利润率", ("ps", "cp_r"), "pct"),
    ("有效税率", ("ps", "ite_tp_r"), "pct"),
    # 费用率指标
    ("销售费用率", ("ps", "se_r"), "pct"),
    ("管理费用率", ("ps", "ae_r"), "pct"),
    ("研发费用率", ("ps", "rade_r"), "pct"),
    ("财务费用率", ("ps", "fe_r"), "pct"),
    ("四项费用率", ("ps", "foe_r"), "pct"),
    # 区域收入
    ("境内收入", ("ps", "d_oi"), "amount"),
    ("海外收入", ("ps", "o_oi"), "amount"),
    ("境内收入占比", ("ps", "d_oi_r"), "pct"),
    ("海外收入占比", ("ps", "o_oi_r"), "pct"),
    ("境内毛利率", ("ps", "d_gp_m"), "pct"),
    ("海外毛利率", ("ps", "o_gp_m"), "pct"),
]

CASH_FLOW_FIELDS: List[Tuple[str, Tuple[str, str], str]] = [
    ("经营活动现金流净额", ("cfs", "ncffoa"), "amount"),
    ("销售商品收到的现金", ("cfs", "crfscapls"), "amount"),
    ("购买商品支付的现金", ("cfs", "cpfpcarls"), "amount"),
    ("支付给职工的现金", ("cfs", "cptofe"), "amount"),
    ("支付的税费", ("cfs", "cpft"), "amount"),
    ("投资活动现金流净额", ("cfs", "ncffia"), "amount"),
    ("购建固定资产支付的现金", ("cfs", "cpfpfiaolta"), "amount"),
    ("收回投资收到的现金", ("cfs", "crfrci"), "amount"),
    ("投资收益收到的现金", ("cfs", "crfii"), "amount"),
    ("筹资活动现金流净额", ("cfs", "ncfffa"), "amount"),
    ("吸收投资收到的现金", ("cfs", "crfai"), "amount"),
    ("取得借款收到的现金", ("cfs", "crfl"), "amount"),
    ("偿还债务支付的现金", ("cfs", "cpfbrp"), "amount"),
    ("分配股利支付的现金", ("cfs", "cpfdapdoi"), "amount"),
    ("现金净增加额", ("cfs", "niicace"), "amount"),
    ("期末现金余额", ("cfs", "bocaceatpe"), "amount"),
]

# ==================== 银行字段 ====================

BANK_BALANCE_SHEET_FIELDS: List[Tuple[str, Tuple[str, str], str]] = [
    # ========== 资产 ==========
    ("总资产", ("bs", "ta"), "amount"),
    ("现金及存放中央银行款项", ("bs", "cabwcb"), "amount"),
    ("存放同业", ("bs", "bwbaofi"), "amount"),
    ("拆出资金", ("bs", "pwbaofi"), "amount"),
    ("买入返售金融资产", ("bs", "fahursa"), "amount"),
    ("发放贷款及垫款", ("bs", "laatc"), "amount"),
    ("衍生金融资产", ("bs", "dfa"), "amount"),
    ("金融投资", ("bs", "t_fi"), "amount"),
    ("以公允价值计量且变动计入当期损益的金融投资", ("bs", "fiafvtpol"), "amount"),
    ("以摊余成本计量的金融投资", ("bs", "fiaac"), "amount"),
    ("以公允价值计量且变动计入其他综合收益的金融投资", ("bs", "fiafvtoci"), "amount"),
    ("长期股权投资", ("bs", "ltei"), "amount"),
    ("固定资产", ("bs", "fa"), "amount"),
    ("无形资产", ("bs", "ia"), "amount"),
    ("商誉", ("bs", "gw"), "amount"),
    ("递延所得税资产", ("bs", "dita"), "amount"),
    ("其他资产", ("bs", "oa"), "amount"),
    # ========== 负债 ==========
    ("负债合计", ("bs", "tl"), "amount"),
    ("向中央银行借款", ("bs", "bfcb"), "amount"),
    ("同业存入及拆入", ("bs", "dapfbaofi"), "amount"),
    ("卖出回购金融资产", ("bs", "fasurpa"), "amount"),
    ("客户存款", ("bs", "cd"), "amount"),
    ("应付债券", ("bs", "bp"), "amount"),
    ("应付职工薪酬", ("bs", "sawp"), "amount"),
    ("应交税费", ("bs", "tp"), "amount"),
    ("递延所得税负债", ("bs", "ditl"), "amount"),
    ("其他负债", ("bs", "ol"), "amount"),
    # ========== 所有者权益 ==========
    ("所有者权益合计", ("bs", "toe"), "amount"),
    ("股本", ("bs", "sc"), "amount"),
    ("其他权益工具", ("bs", "oei"), "amount"),
    ("资本公积", ("bs", "capr"), "amount"),
    ("库存股", ("bs", "is"), "amount"),
    ("其他综合收益", ("bs", "oci"), "amount"),
    ("盈余公积", ("bs", "surr"), "amount"),
    ("一般风险准备金", ("bs", "pogr"), "amount"),
    ("未分配利润", ("bs", "rtp"), "amount"),
    ("归属于母公司股东权益", ("bs", "tetoshopc"), "amount"),
    ("少数股东权益", ("bs", "etmsh"), "amount"),
    # ========== 关键比率 ==========
    ("资产负债率", ("bs", "tl_ta_r"), "pct"),
    ("股东权益占比", ("bs", "toe_ta_r"), "pct"),
    # ========== 资本充足 ==========
    ("风险加权资产", ("bs", "trwa"), "amount"),
    ("核心一级资本充足率", ("bs", "ct1car"), "pct"),
    ("一级资本充足率", ("bs", "t1car"), "pct"),
    ("资本充足率", ("bs", "car"), "pct"),
    ("净利差", ("bs", "nis"), "pct"),
    ("净息差", ("bs", "nim"), "pct"),
    ("流动性覆盖率", ("bs", "lcr"), "pct"),
    # ========== 贷款质量 ==========
    ("贷款和垫款总额", ("bs", "tlaatc"), "amount"),
    ("不良贷款余额", ("bs", "npl"), "amount"),
    ("关注类贷款", ("bs", "sm_pf"), "amount"),
    ("贷款损失准备", ("bs", "llr"), "amount"),
    ("逾期贷款", ("bs", "tol"), "amount"),
    ("逾期90天贷款", ("bs", "lofmt3m"), "amount"),
    ("不良率", ("bs", "npl_tlaatc_r"), "pct"),
    ("拨贷比", ("bs", "llr_tlaatc_r"), "pct"),
    ("拨备覆盖率", ("bs", "llr_npl_r"), "pct"),
]

BANK_INCOME_STATEMENT_FIELDS: List[Tuple[str, Tuple[str, str], str]] = [
    # ========== 营业收入 ==========
    ("营业收入", ("ps", "oi"), "amount"),
    ("净利息收入", ("ps", "nii"), "amount"),
    ("利息收入", ("ps", "ii"), "amount"),
    ("利息支出", ("ps", "ie"), "amount"),
    ("净息收入占比", ("ps", "nii_bi_r"), "pct"),
    ("非息收入", ("ps", "nonii"), "amount"),
    ("非息收入占比", ("ps", "nonii_bi_r"), "pct"),
    ("手续费及佣金净收入", ("ps", "nfaci"), "amount"),
    ("手续费及佣金收入", ("ps", "faci"), "amount"),
    ("手续费及佣金支出", ("ps", "face"), "amount"),
    ("公允价值变动收益", ("ps", "ciofv"), "amount"),
    ("投资收益", ("ps", "ivi"), "amount"),
    # ========== 营业支出 ==========
    ("营业支出", ("ps", "oe"), "amount"),
    ("税金及附加", ("ps", "tas"), "amount"),
    ("业务及管理费用", ("ps", "baae"), "amount"),
    ("收入成本比", ("ps", "c_i_r"), "pct"),
    ("信用减值损失", ("ps", "cilor"), "amount"),
    ("资产减值损失", ("ps", "ailor"), "amount"),
    # ========== 利润 ==========
    ("营业利润", ("ps", "op"), "amount"),
    ("营业利润率", ("ps", "op_s_r"), "pct"),
    ("营业外收入", ("ps", "noi"), "amount"),
    ("营业外支出", ("ps", "noe"), "amount"),
    ("利润总额", ("ps", "tp"), "amount"),
    ("所得税费用", ("ps", "ite"), "amount"),
    ("有效税率", ("ps", "ite_tp_r"), "pct"),
    ("净利润", ("ps", "np"), "amount"),
    ("净利率", ("ps", "np_s_r"), "pct"),
    ("归属于母公司股东的净利润", ("ps", "npatoshopc"), "amount"),
    ("少数股东损益", ("ps", "npatmsh"), "amount"),
    ("扣非归母净利润", ("ps", "npadnrpatoshaopc"), "amount"),
    ("加权ROE", ("ps", "wroe"), "pct"),
    # ========== 每股 ==========
    ("基本每股收益", ("ps", "beps"), "raw"),
    ("稀释每股收益", ("ps", "deps"), "raw"),
    # ========== 综合收益 ==========
    ("综合收益总额", ("ps", "tci"), "amount"),
]

BANK_CASH_FLOW_FIELDS: List[Tuple[str, Tuple[str, str], str]] = [
    # 经营活动
    ("经营活动现金流净额", ("cfs", "ncffoa"), "amount"),
    ("经营活动现金流入小计", ("cfs", "stciffoa"), "amount"),
    ("经营活动现金流出小计", ("cfs", "stcoffoa"), "amount"),
    ("收取利息手续费及佣金的现金", ("cfs", "crfifac"), "amount"),
    ("支付利息手续费及佣金的现金", ("cfs", "cpfifac"), "amount"),
    ("支付给职工的现金", ("cfs", "cptofe"), "amount"),
    ("支付的税费", ("cfs", "cpft"), "amount"),
    # 投资活动
    ("投资活动现金流净额", ("cfs", "ncffia"), "amount"),
    ("收回投资收到的现金", ("cfs", "crfrci"), "amount"),
    ("投资所支付的现金", ("cfs", "cpfi"), "amount"),
    # 筹资活动
    ("筹资活动现金流净额", ("cfs", "ncfffa"), "amount"),
    ("吸收投资收到的现金", ("cfs", "crfai"), "amount"),
    ("偿付债务支付的现金", ("cfs", "cpfbrp"), "amount"),
    ("分配股利支付的现金", ("cfs", "cpfdapdoi"), "amount"),
    # 汇总
    ("现金净增加额", ("cfs", "niicace"), "amount"),
    ("期末现金余额", ("cfs", "bocaceatpe"), "amount"),
]

# ==================== 保险字段 ====================

INSURANCE_BALANCE_SHEET_FIELDS: List[Tuple[str, Tuple[str, str], str]] = [
    # ========== 资产 ==========
    ("总资产", ("bs", "ta"), "amount"),
    ("货币资金", ("bs", "cabb"), "amount"),
    ("拆出资金", ("bs", "pwbaofi"), "amount"),
    ("买入返售金融资产", ("bs", "fahursa"), "amount"),
    ("应收保费", ("bs", "pr"), "amount"),
    ("发放贷款及垫款", ("bs", "laatc"), "amount"),
    ("衍生金融资产", ("bs", "dfa"), "amount"),
    ("金融投资", ("bs", "t_fi"), "amount"),
    ("以公允价值计量且变动计入当期损益的金融投资", ("bs", "fiafvtpol"), "amount"),
    ("以摊余成本计量的金融投资", ("bs", "fiaac"), "amount"),
    ("以公允价值计量且变动计入其他综合收益的债务工具投资", ("bs", "diafvtoci"), "amount"),
    ("保险合同资产", ("bs", "ica"), "amount"),
    ("长期股权投资", ("bs", "ltei"), "amount"),
    ("固定资产", ("bs", "fa"), "amount"),
    ("无形资产", ("bs", "ia"), "amount"),
    ("商誉", ("bs", "gw"), "amount"),
    ("递延所得税资产", ("bs", "dita"), "amount"),
    ("其他资产", ("bs", "oa"), "amount"),
    # ========== 负债 ==========
    ("负债合计", ("bs", "tl"), "amount"),
    ("短期借款", ("bs", "stl"), "amount"),
    ("拆入资金", ("bs", "pfbaofi"), "amount"),
    ("卖出回购金融资产", ("bs", "fasurpa"), "amount"),
    ("保险合同负债", ("bs", "icl"), "amount"),
    ("应付职工薪酬", ("bs", "sawp"), "amount"),
    ("应交税费", ("bs", "tp"), "amount"),
    ("应付债券", ("bs", "bp"), "amount"),
    ("递延所得税负债", ("bs", "ditl"), "amount"),
    ("其他负债", ("bs", "ol"), "amount"),
    # ========== 所有者权益 ==========
    ("所有者权益合计", ("bs", "toe"), "amount"),
    ("股本", ("bs", "sc"), "amount"),
    ("其他权益工具", ("bs", "oei"), "amount"),
    ("资本公积", ("bs", "capr"), "amount"),
    ("库存股", ("bs", "is"), "amount"),
    ("其他综合收益", ("bs", "oci"), "amount"),
    ("盈余公积", ("bs", "surr"), "amount"),
    ("一般风险准备金", ("bs", "pogr"), "amount"),
    ("未分配利润", ("bs", "rtp"), "amount"),
    ("归属于母公司股东权益", ("bs", "tetoshopc"), "amount"),
    ("少数股东权益", ("bs", "etmsh"), "amount"),
    # ========== 关键比率 ==========
    ("资产负债率", ("bs", "tl_ta_r"), "pct"),
    ("股东权益占比", ("bs", "toe_ta_r"), "pct"),
    # ========== 内含价值与偿付能力 ==========
    ("内含价值", ("bs", "ev"), "amount"),
    ("寿险及健康险业务内含价值", ("bs", "evolahib"), "amount"),
    ("核心偿付能力充足率", ("bs", "coresr"), "pct"),
    ("综合偿付能力充足率", ("bs", "compsr"), "pct"),
]

INSURANCE_INCOME_STATEMENT_FIELDS: List[Tuple[str, Tuple[str, str], str]] = [
    # ========== 营业收入 ==========
    ("营业收入", ("ps", "oi"), "amount"),
    ("保险服务收入", ("ps", "ir"), "amount"),
    ("银行业务利息净收入", ("ps", "niifb"), "amount"),
    ("非保险业务手续费及佣金净收入", ("ps", "nnifaci"), "amount"),
    ("投资收益", ("ps", "ivi"), "amount"),
    ("公允价值变动收益", ("ps", "ciofv"), "amount"),
    ("其他收益", ("ps", "oic"), "amount"),
    # ========== 营业支出 ==========
    ("营业支出", ("ps", "oe"), "amount"),
    ("保险服务费用", ("ps", "ise"), "amount"),
    ("税金及附加", ("ps", "tas"), "amount"),
    ("业务及管理费用", ("ps", "baae"), "amount"),
    ("信用减值损失", ("ps", "cilor"), "amount"),
    ("资产减值损失", ("ps", "ailor"), "amount"),
    # ========== 利润 ==========
    ("营业利润", ("ps", "op"), "amount"),
    ("营业利润率", ("ps", "op_s_r"), "pct"),
    ("营业外收入", ("ps", "noi"), "amount"),
    ("营业外支出", ("ps", "noe"), "amount"),
    ("利润总额", ("ps", "tp"), "amount"),
    ("所得税费用", ("ps", "ite"), "amount"),
    ("有效税率", ("ps", "ite_tp_r"), "pct"),
    ("净利润", ("ps", "np"), "amount"),
    ("净利率", ("ps", "np_s_r"), "pct"),
    ("归属于母公司股东的净利润", ("ps", "npatoshopc"), "amount"),
    ("少数股东损益", ("ps", "npatmsh"), "amount"),
    ("扣非归母净利润", ("ps", "npadnrpatoshaopc"), "amount"),
    ("新业务价值", ("ps", "nbv"), "amount"),
    ("加权ROE", ("ps", "wroe"), "pct"),
    # ========== 每股 ==========
    ("基本每股收益", ("ps", "beps"), "raw"),
    ("稀释每股收益", ("ps", "deps"), "raw"),
    ("综合收益总额", ("ps", "tci"), "amount"),
]

INSURANCE_CASH_FLOW_FIELDS: List[Tuple[str, Tuple[str, str], str]] = [
    ("经营活动现金流净额", ("cfs", "ncffoa"), "amount"),
    ("经营活动现金流入小计", ("cfs", "stciffoa"), "amount"),
    ("经营活动现金流出小计", ("cfs", "stcoffoa"), "amount"),
    ("收取利息手续费及佣金的现金", ("cfs", "crfifac"), "amount"),
    ("支付给职工的现金", ("cfs", "cptofe"), "amount"),
    ("支付的税费", ("cfs", "cpft"), "amount"),
    ("投资活动现金流净额", ("cfs", "ncffia"), "amount"),
    ("收回投资收到的现金", ("cfs", "crfrci"), "amount"),
    ("投资所支付的现金", ("cfs", "cpfi"), "amount"),
    ("筹资活动现金流净额", ("cfs", "ncfffa"), "amount"),
    ("吸收投资收到的现金", ("cfs", "crfai"), "amount"),
    ("偿付债务支付的现金", ("cfs", "cpfbrp"), "amount"),
    ("分配股利支付的现金", ("cfs", "cpfdapdoi"), "amount"),
    ("现金净增加额", ("cfs", "niicace"), "amount"),
    ("期末现金余额", ("cfs", "bocaceatpe"), "amount"),
]

# ==================== 证券字段 ====================

SECURITY_BALANCE_SHEET_FIELDS: List[Tuple[str, Tuple[str, str], str]] = [
    # ========== 资产 ==========
    ("总资产", ("bs", "ta"), "amount"),
    ("货币资金", ("bs", "cabb"), "amount"),
    ("结算备付金", ("bs", "sr"), "amount"),
    ("融出资金", ("bs", "ma"), "amount"),
    ("衍生金融资产", ("bs", "dfa"), "amount"),
    ("买入返售金融资产", ("bs", "fahursa"), "amount"),
    ("金融投资", ("bs", "t_fi"), "amount"),
    ("以公允价值计量且变动计入当期损益的金融投资", ("bs", "fiafvtpol"), "amount"),
    ("以摊余成本计量的金融投资", ("bs", "fiaac"), "amount"),
    ("以公允价值计量且变动计入其他综合收益的债务工具投资", ("bs", "diafvtoci"), "amount"),
    ("长期股权投资", ("bs", "ltei"), "amount"),
    ("固定资产", ("bs", "fa"), "amount"),
    ("无形资产", ("bs", "ia"), "amount"),
    ("商誉", ("bs", "gw"), "amount"),
    ("递延所得税资产", ("bs", "dita"), "amount"),
    ("其他资产", ("bs", "oa"), "amount"),
    # ========== 负债 ==========
    ("负债合计", ("bs", "tl"), "amount"),
    ("短期借款", ("bs", "stl"), "amount"),
    ("拆入资金", ("bs", "pfbaofi"), "amount"),
    ("卖出回购金融资产", ("bs", "fasurpa"), "amount"),
    ("代理买卖证券款", ("bs", "stoa"), "amount"),
    ("代理承销证券款", ("bs", "ssoa"), "amount"),
    ("应付债券", ("bs", "bp"), "amount"),
    ("应付职工薪酬", ("bs", "sawp"), "amount"),
    ("应交税费", ("bs", "tp"), "amount"),
    ("递延所得税负债", ("bs", "ditl"), "amount"),
    ("其他负债", ("bs", "ol"), "amount"),
    # ========== 所有者权益 ==========
    ("所有者权益合计", ("bs", "toe"), "amount"),
    ("股本", ("bs", "sc"), "amount"),
    ("其他权益工具", ("bs", "oei"), "amount"),
    ("资本公积", ("bs", "capr"), "amount"),
    ("库存股", ("bs", "is"), "amount"),
    ("其他综合收益", ("bs", "oci"), "amount"),
    ("盈余公积", ("bs", "surr"), "amount"),
    ("一般风险准备金", ("bs", "pogr"), "amount"),
    ("未分配利润", ("bs", "rtp"), "amount"),
    ("归属于母公司股东权益", ("bs", "tetoshopc"), "amount"),
    ("少数股东权益", ("bs", "etmsh"), "amount"),
    # ========== 关键比率 ==========
    ("资产负债率", ("bs", "tl_ta_r"), "pct"),
    ("股东权益占比", ("bs", "toe_ta_r"), "pct"),
    # ========== 券商风控指标 ==========
    ("净资本", ("bs", "pc_nc"), "amount"),
    ("核心净资本", ("bs", "pc_cnc"), "amount"),
    ("风险覆盖率", ("bs", "pc_rcr"), "pct"),
    ("资本杠杆率", ("bs", "pc_clr"), "pct"),
    ("流动性覆盖率", ("bs", "pc_lcr"), "pct"),
    ("净稳定资金率", ("bs", "pc_nsfr"), "pct"),
]

SECURITY_INCOME_STATEMENT_FIELDS: List[Tuple[str, Tuple[str, str], str]] = [
    # ========== 营业收入 ==========
    ("营业收入", ("ps", "oi"), "amount"),
    ("净利息收入", ("ps", "nii"), "amount"),
    ("利息收入", ("ps", "ii"), "amount"),
    ("利息支出", ("ps", "ie"), "amount"),
    ("手续费及佣金净收入", ("ps", "nfaci"), "amount"),
    ("经纪业务净收入", ("ps", "nfifb"), "amount"),
    ("投资银行业务净收入", ("ps", "nfifib"), "amount"),
    ("资产管理业务净收入", ("ps", "nfifam"), "amount"),
    ("投资收益", ("ps", "ivi"), "amount"),
    ("公允价值变动收益", ("ps", "ciofv"), "amount"),
    ("其他收益", ("ps", "oic"), "amount"),
    # ========== 营业支出 ==========
    ("营业支出", ("ps", "oe"), "amount"),
    ("税金及附加", ("ps", "tas"), "amount"),
    ("业务及管理费用", ("ps", "baae"), "amount"),
    ("信用减值损失", ("ps", "cilor"), "amount"),
    ("资产减值损失", ("ps", "ailor"), "amount"),
    # ========== 利润 ==========
    ("营业利润", ("ps", "op"), "amount"),
    ("营业利润率", ("ps", "op_s_r"), "pct"),
    ("营业外收入", ("ps", "noi"), "amount"),
    ("营业外支出", ("ps", "noe"), "amount"),
    ("利润总额", ("ps", "tp"), "amount"),
    ("所得税费用", ("ps", "ite"), "amount"),
    ("有效税率", ("ps", "ite_tp_r"), "pct"),
    ("净利润", ("ps", "np"), "amount"),
    ("净利率", ("ps", "np_s_r"), "pct"),
    ("归属于母公司股东的净利润", ("ps", "npatoshopc"), "amount"),
    ("少数股东损益", ("ps", "npatmsh"), "amount"),
    ("扣非归母净利润", ("ps", "npadnrpatoshaopc"), "amount"),
    ("加权ROE", ("ps", "wroe"), "pct"),
    # ========== 每股 ==========
    ("基本每股收益", ("ps", "beps"), "raw"),
    ("稀释每股收益", ("ps", "deps"), "raw"),
    ("综合收益总额", ("ps", "tci"), "amount"),
]

SECURITY_CASH_FLOW_FIELDS: List[Tuple[str, Tuple[str, str], str]] = [
    ("经营活动现金流净额", ("cfs", "ncffoa"), "amount"),
    ("经营活动现金流入小计", ("cfs", "stciffoa"), "amount"),
    ("经营活动现金流出小计", ("cfs", "stcoffoa"), "amount"),
    ("收取利息手续费及佣金的现金", ("cfs", "crfifac"), "amount"),
    ("支付利息手续费及佣金的现金", ("cfs", "cpfifac"), "amount"),
    ("支付给职工的现金", ("cfs", "cptofe"), "amount"),
    ("支付的税费", ("cfs", "cpft"), "amount"),
    ("投资活动现金流净额", ("cfs", "ncffia"), "amount"),
    ("收回投资收到的现金", ("cfs", "crfrci"), "amount"),
    ("投资所支付的现金", ("cfs", "cpfi"), "amount"),
    ("筹资活动现金流净额", ("cfs", "ncfffa"), "amount"),
    ("吸收投资收到的现金", ("cfs", "crfai"), "amount"),
    ("偿付债务支付的现金", ("cfs", "cpfbrp"), "amount"),
    ("分配股利支付的现金", ("cfs", "cpfdapdoi"), "amount"),
    ("现金净增加额", ("cfs", "niicace"), "amount"),
    ("期末现金余额", ("cfs", "bocaceatpe"), "amount"),
]

# ==================== 其它金融字段 ====================

OTHER_FINANCIAL_BALANCE_SHEET_FIELDS: List[Tuple[str, Tuple[str, str], str]] = [
    # ========== 资产 ==========
    ("总资产", ("bs", "ta"), "amount"),
    ("货币资金", ("bs", "cabb"), "amount"),
    ("拆出资金", ("bs", "pwbaofi"), "amount"),
    ("应收账款", ("bs", "ar"), "amount"),
    ("长期股权投资", ("bs", "ltei"), "amount"),
    ("固定资产", ("bs", "fa"), "amount"),
    ("无形资产", ("bs", "ia"), "amount"),
    ("商誉", ("bs", "gw"), "amount"),
    ("递延所得税资产", ("bs", "dita"), "amount"),
    ("其他资产", ("bs", "oa"), "amount"),
    # ========== 负债 ==========
    ("负债合计", ("bs", "tl"), "amount"),
    ("短期借款", ("bs", "stl"), "amount"),
    ("拆入资金", ("bs", "pfbaofi"), "amount"),
    ("应付债券", ("bs", "bp"), "amount"),
    ("应付职工薪酬", ("bs", "sawp"), "amount"),
    ("应交税费", ("bs", "tp"), "amount"),
    ("长期借款", ("bs", "ltl"), "amount"),
    ("递延所得税负债", ("bs", "ditl"), "amount"),
    ("其他负债", ("bs", "ol"), "amount"),
    # ========== 所有者权益 ==========
    ("所有者权益合计", ("bs", "toe"), "amount"),
    ("股本", ("bs", "sc"), "amount"),
    ("其他权益工具", ("bs", "oei"), "amount"),
    ("资本公积", ("bs", "capr"), "amount"),
    ("库存股", ("bs", "is"), "amount"),
    ("其他综合收益", ("bs", "oci"), "amount"),
    ("盈余公积", ("bs", "surr"), "amount"),
    ("一般风险准备金", ("bs", "pogr"), "amount"),
    ("未分配利润", ("bs", "rtp"), "amount"),
    ("归属于母公司股东权益", ("bs", "tetoshopc"), "amount"),
    ("少数股东权益", ("bs", "etmsh"), "amount"),
    # ========== 关键比率 ==========
    ("资产负债率", ("bs", "tl_ta_r"), "pct"),
    ("股东权益占比", ("bs", "toe_ta_r"), "pct"),
]

OTHER_FINANCIAL_INCOME_STATEMENT_FIELDS: List[Tuple[str, Tuple[str, str], str]] = [
    # ========== 营业收入 ==========
    ("营业收入", ("ps", "oi"), "amount"),
    ("净利息收入", ("ps", "nii"), "amount"),
    ("利息收入", ("ps", "ii"), "amount"),
    ("利息支出", ("ps", "ie"), "amount"),
    ("手续费及佣金净收入", ("ps", "nfaci"), "amount"),
    ("投资收益", ("ps", "ivi"), "amount"),
    ("公允价值变动收益", ("ps", "ciofv"), "amount"),
    ("其他收益", ("ps", "oic"), "amount"),
    # ========== 营业支出 ==========
    ("营业支出", ("ps", "oe"), "amount"),
    ("税金及附加", ("ps", "tas"), "amount"),
    ("业务及管理费用", ("ps", "baae"), "amount"),
    ("信用减值损失", ("ps", "cilor"), "amount"),
    ("资产减值损失", ("ps", "ailor"), "amount"),
    # ========== 利润 ==========
    ("营业利润", ("ps", "op"), "amount"),
    ("营业利润率", ("ps", "op_s_r"), "pct"),
    ("营业外收入", ("ps", "noi"), "amount"),
    ("营业外支出", ("ps", "noe"), "amount"),
    ("利润总额", ("ps", "tp"), "amount"),
    ("所得税费用", ("ps", "ite"), "amount"),
    ("有效税率", ("ps", "ite_tp_r"), "pct"),
    ("净利润", ("ps", "np"), "amount"),
    ("净利率", ("ps", "np_s_r"), "pct"),
    ("归属于母公司股东的净利润", ("ps", "npatoshopc"), "amount"),
    ("少数股东损益", ("ps", "npatmsh"), "amount"),
    ("扣非归母净利润", ("ps", "npadnrpatoshaopc"), "amount"),
    ("加权ROE", ("ps", "wroe"), "pct"),
    # ========== 每股 ==========
    ("基本每股收益", ("ps", "beps"), "raw"),
    ("稀释每股收益", ("ps", "deps"), "raw"),
    ("综合收益总额", ("ps", "tci"), "amount"),
]

OTHER_FINANCIAL_CASH_FLOW_FIELDS: List[Tuple[str, Tuple[str, str], str]] = [
    ("经营活动现金流净额", ("cfs", "ncffoa"), "amount"),
    ("经营活动现金流入小计", ("cfs", "stciffoa"), "amount"),
    ("经营活动现金流出小计", ("cfs", "stcoffoa"), "amount"),
    ("收取利息手续费及佣金的现金", ("cfs", "crfifac"), "amount"),
    ("支付给职工的现金", ("cfs", "cptofe"), "amount"),
    ("支付的税费", ("cfs", "cpft"), "amount"),
    ("投资活动现金流净额", ("cfs", "ncffia"), "amount"),
    ("收回投资收到的现金", ("cfs", "crfrci"), "amount"),
    ("筹资活动现金流净额", ("cfs", "ncfffa"), "amount"),
    ("吸收投资收到的现金", ("cfs", "crfai"), "amount"),
    ("偿付债务支付的现金", ("cfs", "cpfbrp"), "amount"),
    ("分配股利支付的现金", ("cfs", "cpfdapdoi"), "amount"),
    ("现金净增加额", ("cfs", "niicace"), "amount"),
    ("期末现金余额", ("cfs", "bocaceatpe"), "amount"),
]

# ==================== 类型分发 ====================

FS_TYPE_FIELDS = {
    "non_financial": (BALANCE_SHEET_FIELDS, INCOME_STATEMENT_FIELDS, CASH_FLOW_FIELDS),
    "bank": (BANK_BALANCE_SHEET_FIELDS, BANK_INCOME_STATEMENT_FIELDS, BANK_CASH_FLOW_FIELDS),
    "insurance": (INSURANCE_BALANCE_SHEET_FIELDS, INSURANCE_INCOME_STATEMENT_FIELDS, INSURANCE_CASH_FLOW_FIELDS),
    "security": (SECURITY_BALANCE_SHEET_FIELDS, SECURITY_INCOME_STATEMENT_FIELDS, SECURITY_CASH_FLOW_FIELDS),
    "other_financial": (OTHER_FINANCIAL_BALANCE_SHEET_FIELDS, OTHER_FINANCIAL_INCOME_STATEMENT_FIELDS, OTHER_FINANCIAL_CASH_FLOW_FIELDS),
}


class JsonGenerator:
    """JSON数据生成器"""

    def __init__(self, data: Dict[str, Any], stock_code: str, fs_type: str = "non_financial"):
        self.data = data
        self.stock_code = stock_code
        self.fs_type = fs_type
        bs_fields, ps_fields, cfs_fields = FS_TYPE_FIELDS.get(fs_type, FS_TYPE_FIELDS["non_financial"])
        self._bs_fields = bs_fields
        self._ps_fields = ps_fields
        self._cfs_fields = cfs_fields

    def _format_value(self, value: Any, fmt_type: str) -> Any:
        """根据格式类型转换数值"""
        if value is None:
            return None
        if fmt_type == "amount":
            return _fmt_amount(value)
        elif fmt_type == "pct":
            return _fmt_pct(value)
        elif fmt_type == "ratio":
            return round(value, 2) if isinstance(value, (int, float)) else value
        elif fmt_type == "raw":
            return round(value, 2) if isinstance(value, (int, float)) else value
        return value

    def _build_time_series(self, data_list: list, fields: list) -> List[Dict]:
        """
        将API时序数据转换为按报告期组织的字典列表。
        保留：所有年报（12-31）+ 最近8个季度（2年），支持年度趋势和季度同比。
        """
        if not data_list:
            return []

        # 按日期倒序
        sorted_data = sorted(data_list, key=lambda x: x.get("date", ""), reverse=True)

        # 筛选：最近8个季度（支持同比）+ 所有年报（12-31），去重保序
        selected = []
        seen_dates = set()
        for i, record in enumerate(sorted_data):
            date_str = _fmt_date(record.get("date")) or ""
            if date_str in seen_dates:
                continue
            if i < 8 or date_str.endswith("-12-31"):
                selected.append(record)
                seen_dates.add(date_str)

        result = []
        for record in selected:
            row = {"报告期": _fmt_date(record.get("date"))}

            for cn_name, field_path, fmt_type in fields:
                table, field = field_path
                value = _get_field(record, table, field)
                formatted = self._format_value(value, fmt_type)
                if formatted is not None:
                    row[cn_name] = formatted

            result.append(row)

        return result

    def build_basic_info(self) -> Dict:
        """基础信息"""
        basic = self.data.get("basic_info", {})
        indices = self.data.get("indices", [])

        info = {
            "公司名称": basic.get("name"),
            "股票代码": basic.get("stockCode"),
            "市场": basic.get("market"),
            "交易所": basic.get("exchange"),
            "上市日期": _fmt_date(basic.get("ipoDate")),
            "上市状态": basic.get("listingStatus"),
            "互联互通": bool(basic.get("mutualMarketFlag")),
            "融资融券": bool(basic.get("marginTradingAndSecuritiesLendingFlag")),
        }

        if indices:
            info["所属指数"] = [
                {"名称": idx.get("name"), "代码": idx.get("stockCode")}
                for idx in indices[:20]
            ]

        return info

    def build_profile(self) -> Dict:
        """公司概况"""
        profile = self.data.get("profile", {})
        industries = self.data.get("industries", [])
        shareholders = self.data.get("shareholders", [])

        # 实际控制人类型
        controller_type_map = {
            "natural_person": "自然人",
            "collective": "集体",
            "foreign_company": "外企",
            "state_owned": "国有",
        }
        controller_types = profile.get("actualControllerTypes", [])
        controller_type_str = "、".join(
            [controller_type_map.get(t, t) for t in controller_types]
        ) if controller_types else None

        # 历史名称
        history_names = profile.get("historyStockNames", [])
        if history_names and isinstance(history_names[0], dict):
            sorted_history = sorted(history_names, key=lambda x: x.get("date", ""))
            names = [sorted_history[0].get("oldName", "")]
            for h in sorted_history:
                names.append(h.get("newName", ""))
            history_names_str = " → ".join([n for n in names if n])
        elif history_names:
            history_names_str = " → ".join(history_names)
        else:
            history_names_str = None

        result = {
            "公司全称": profile.get("companyName"),
            "历史名称": history_names_str,
            "省份": profile.get("province"),
            "城市": profile.get("city"),
            "成立日期": _fmt_date(profile.get("establishDate")),
            "注册资本_万元": profile.get("registeredCapital"),
            "实际控制人类型": controller_type_str,
            "实际控制人": profile.get("actualControllerName"),
            "法人代表": profile.get("legalRepresentative"),
            "董事长": profile.get("chairman"),
            "总经理": profile.get("generalManager"),
            "董秘": profile.get("boardSecretory"),
            "网址": profile.get("website"),
            "主营业务": profile.get("mainBusiness"),
            "经营范围": profile.get("businessScope"),
            "公司简介": profile.get("profile"),
        }

        if industries:
            result["所属行业"] = [
                {"名称": ind.get("name"), "来源": ind.get("source")}
                for ind in industries
            ]

        if shareholders:
            latest_date = shareholders[0].get("date")
            latest = [s for s in shareholders if s.get("date") == latest_date]
            result["前十大股东"] = {
                "日期": _fmt_date(latest_date),
                "股东": [
                    {
                        "名称": sh.get("name"),
                        "持股数量_万股": round(sh.get("holdings", 0) / 1e4, 2) if sh.get("holdings") else None,
                        "持股比例": _fmt_pct(sh.get("proportionOfCapitalization")),
                        "性质": sh.get("property"),
                    }
                    for sh in latest[:10]
                ]
            }

        return result

    def build_balance_sheet(self) -> List[Dict]:
        """资产负债表（单位：金额为亿元，比率为%）"""
        return self._build_time_series(
            self.data.get("balance_sheet", []),
            self._bs_fields
        )

    def build_income_statement(self) -> List[Dict]:
        """利润表（单位：金额为亿元，比率为%）"""
        return self._build_time_series(
            self.data.get("income_statement", []),
            self._ps_fields
        )

    def build_cash_flow(self) -> List[Dict]:
        """现金流量表（单位：亿元）"""
        return self._build_time_series(
            self.data.get("cash_flow", []),
            self._cfs_fields
        )

    def build_revenue(self) -> Dict:
        """营收构成与经营数据"""
        revenue_data = self.data.get("revenue_constitution", [])
        operating_data = self.data.get("operating_data", [])

        result = {}

        if revenue_data:
            items = []
            for record in revenue_data[:50]:
                date = _fmt_date(record.get("date"))
                for item in record.get("dataList", []):
                    entry = {
                        "报告期": date,
                        "分类方式": item.get("classifyType"),
                        "项目名称": item.get("itemName"),
                    }
                    if item.get("revenue") is not None:
                        entry["收入_亿元"] = _fmt_amount(item["revenue"])
                    if item.get("revenuePercentage") is not None:
                        entry["收入占比"] = round(item["revenuePercentage"], 2)
                    if item.get("grossProfitMargin") is not None:
                        entry["毛利率"] = _fmt_pct(item["grossProfitMargin"])
                    items.append(entry)
            result["营收构成"] = items

        if operating_data:
            items = []
            for record in operating_data[:50]:
                date = _fmt_date(record.get("date"))
                for item in record.get("dataList", []):
                    items.append({
                        "报告期": date,
                        "项目名称": item.get("itemName"),
                        "数值": item.get("value"),
                        "单位": item.get("unitText"),
                    })
            result["经营数据"] = items

        return result

    def build_fundamental(self) -> List[Dict]:
        """基本面数据（股息率、估值等）

        从日频数据中筛选：最新一条 + 每年年末（12-31附近的最后一个交易日）。
        """
        data_list = self.data.get("fundamental", [])
        if not data_list:
            return []

        sorted_data = sorted(data_list, key=lambda x: x.get("date", ""), reverse=True)

        # 筛选：最新一条 + 每年最后一条（按年份分组取最晚日期）
        selected = []
        seen_years = set()
        for i, record in enumerate(sorted_data):
            date_str = _fmt_date(record.get("date")) or ""
            year = date_str[:4]
            if i == 0:
                selected.append(record)
                seen_years.add(year)
            elif year and year not in seen_years:
                selected.append(record)
                seen_years.add(year)

        result = []
        for record in selected:
            row = {"日期": _fmt_date(record.get("date"))}
            if record.get("dyr") is not None:
                row["股息率"] = _fmt_pct(record["dyr"])
            if record.get("pe_ttm") is not None:
                row["PE_TTM"] = round(record["pe_ttm"], 2) if isinstance(record["pe_ttm"], (int, float)) else record["pe_ttm"]
            if record.get("pb") is not None:
                row["PB"] = round(record["pb"], 2) if isinstance(record["pb"], (int, float)) else record["pb"]
            if record.get("mc") is not None:
                row["总市值_亿元"] = _fmt_amount(record["mc"])
            result.append(row)

        return result

    def build_regulation(self) -> Dict:
        """监管信息"""
        measures = self.data.get("measures", [])
        inquiry = self.data.get("inquiry", [])

        result = {}

        if measures:
            result["监管措施"] = [
                {
                    "日期": _fmt_date(m.get("date")),
                    "类型": m.get("displayTypeText"),
                    "说明": m.get("linkText"),
                    "对象": m.get("referent"),
                }
                for m in measures
            ]

        if inquiry:
            result["问询函"] = [
                {
                    "日期": _fmt_date(i.get("date")),
                    "类型": i.get("displayTypeText"),
                    "说明": i.get("linkText"),
                }
                for i in inquiry
            ]

        return result

    def generate(self, output_path: str) -> str:
        """生成完整JSON文件"""
        result = {
            "股票代码": self.stock_code,
            "报表类型": self.fs_type,
            "说明": {
                "金额单位": "亿元",
                "百分比单位": "%",
                "每股指标单位": "元",
                "股息率": "近12个月每股分红(含中期分红)/当日股价，来自理杏仁",
            },
            "基础信息": self.build_basic_info(),
            "公司概况": self.build_profile(),
            "资产负债表": self.build_balance_sheet(),
            "利润表": self.build_income_statement(),
            "现金流量表": self.build_cash_flow(),
            "基本面数据": self.build_fundamental(),
        }

        # 确保目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return output_path
