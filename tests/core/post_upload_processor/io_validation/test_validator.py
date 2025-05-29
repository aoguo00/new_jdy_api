# tests/core/post_upload_processor/io_validation/test_validator.py
import unittest
import pandas as pd
import numpy as np # 用于创建 NaN 值
import os
import tempfile
import shutil

# 导入需要测试的模块和常量
# 注意：根据实际项目结构调整导入路径
from core.post_upload_processor.io_validation import constants as C
from core.post_upload_processor.io_validation.validator import (
    ValidationContext,
    HmiDescriptionConsistencyRule,
    ReservedPointEmptyRule,
    NonReservedRequiredRule,
    PowerSupplyValueRule,
    WiringSystemValueRule,
    RangeRequiredAiRule,
    RangeNumericAiRule,
    SetpointNumericAiRule,
    ReservedAiSpecificEmptyRule,
    RealSetpointUniquenessRule,
    _validate_row_with_rules,
    _validate_main_io_sheet,
    _validate_third_party_sheet,
    validate_io_table,
    BoolSetpointEmptyRule,
    AlwaysRequiredRule,
    HmiNameUniquenessRule
)

# 全局常量定义，方便测试用例使用
TEST_SHEET_NAME = "TestSheet"
TEST_EXCEL_ROW_NUM = 5 # 假设 Excel 行号为 5 (Dataframe index + 2)

class TestValidationRules(unittest.TestCase):

    def _create_context(self, data: dict, sheet_name=TEST_SHEET_NAME, row_num=TEST_EXCEL_ROW_NUM) -> ValidationContext:
        """辅助函数：根据字典创建测试用的 ValidationContext。"""
        # 确保所有可能的列都存在，即使值为 None 或 NaN
        all_cols = [
            C.HMI_NAME_COL, C.DESCRIPTION_COL, C.POWER_SUPPLY_TYPE_COL,
            C.WIRING_SYSTEM_COL, C.MODULE_TYPE_COL, C.RANGE_LOW_LIMIT_COL,
            C.RANGE_HIGH_LIMIT_COL, C.SLL_SET_COL, C.SL_SET_COL, C.SH_SET_COL,
            C.SHH_SET_COL, C.TP_INPUT_VAR_NAME_COL, C.TP_INPUT_DATA_TYPE_COL,
            C.TP_INPUT_SLL_SET_COL, C.TP_INPUT_SL_SET_COL, C.TP_INPUT_SH_SET_COL,
            C.TP_INPUT_SHH_SET_COL
        ]
        full_data = {col: data.get(col, np.nan) for col in all_cols}
        row = pd.Series(full_data)
        return ValidationContext(row, row_num, sheet_name)

    def assertHasError(self, errors: list, substring: str):
        """断言错误列表中包含特定子字符串。"""
        self.assertTrue(any(substring in error for error in errors),
                        f"错误列表中未找到包含 '{substring}' 的错误。错误列表: {errors}")

    def assertNotHasError(self, errors: list, substring: str):
        """断言错误列表中不包含特定子字符串。"""
        self.assertFalse(any(substring in error for error in errors),
                         f"错误列表中意外找到包含 '{substring}' 的错误。错误列表: {errors}")

    # --- 开始测试各个规则 ---

    def test_hmi_description_consistency_rule(self):
        """测试 HMI 名称和描述一致性规则。"""
        rule = HmiDescriptionConsistencyRule()

        # 1. 两者都填写 (有效)
        context_valid1 = self._create_context({C.HMI_NAME_COL: "Tag1", C.DESCRIPTION_COL: "Desc1"})
        self.assertEqual(rule.validate(context_valid1), [], "两者都填写时应无错误")

        # 2. 两者都为空 (有效 - 使用 np.nan 模拟空值)
        context_valid2 = self._create_context({C.HMI_NAME_COL: np.nan, C.DESCRIPTION_COL: None})
        self.assertEqual(rule.validate(context_valid2), [], "两者都为空时应无错误")

        # 3. HMI 填写，描述为空 (无效)
        context_invalid1 = self._create_context({C.HMI_NAME_COL: "Tag1", C.DESCRIPTION_COL: ""})
        errors1 = rule.validate(context_invalid1)
        self.assertEqual(len(errors1), 1, "HMI 填写，描述为空时应有1个错误")
        self.assertHasError(errors1, "状态不一致")
        self.assertHasError(errors1, f'"{C.HMI_NAME_COL}"(已填写)')
        self.assertHasError(errors1, f'"{C.DESCRIPTION_COL}"(为空)')


        # 4. HMI 为空，描述填写 (无效)
        context_invalid2 = self._create_context({C.HMI_NAME_COL: None, C.DESCRIPTION_COL: "Desc1"})
        errors2 = rule.validate(context_invalid2)
        self.assertEqual(len(errors2), 1, "HMI 为空，描述填写时应有1个错误")
        self.assertHasError(errors2, "状态不一致")
        self.assertHasError(errors2, f'"{C.HMI_NAME_COL}"(为空)')
        self.assertHasError(errors2, f'"{C.DESCRIPTION_COL}"(已填写)')

    def test_reserved_point_empty_rule(self):
        """测试预留点位某些列必须为空的规则。"""
        rule = ReservedPointEmptyRule(C.POWER_SUPPLY_TYPE_COL, "供电类型（有源/无源）")

        # 1. 非预留点位，列有值 (忽略)
        context_non_reserved = self._create_context({
            C.HMI_NAME_COL: "Tag1", # 非预留
            C.POWER_SUPPLY_TYPE_COL: C.ALLOWED_POWER_SUPPLY_VALUES[0]
        })
        self.assertEqual(rule.validate(context_non_reserved), [], "非预留点位不应触发此规则")

        # 2. 预留点位，列为空 (有效)
        context_reserved_empty = self._create_context({
            C.HMI_NAME_COL: np.nan, # 预留
            C.POWER_SUPPLY_TYPE_COL: None
        })
        self.assertEqual(rule.validate(context_reserved_empty), [], "预留点位且列为空时应无错误")

        # 3. 预留点位，列有值 (无效)
        context_reserved_filled = self._create_context({
            C.HMI_NAME_COL: None, # 预留
            C.POWER_SUPPLY_TYPE_COL: C.ALLOWED_POWER_SUPPLY_VALUES[0]
        })
        errors = rule.validate(context_reserved_filled)
        self.assertEqual(len(errors), 1, "预留点位且列有值时应有1个错误")
        self.assertHasError(errors, "预留点位的此列必须为空")
        self.assertHasError(errors, f'"{C.POWER_SUPPLY_TYPE_COL}"')

    def test_non_reserved_required_rule(self):
        """测试非预留点位某些列必须填写的规则。"""
        rule = NonReservedRequiredRule(C.POWER_SUPPLY_TYPE_COL, "供电类型（有源/无源）")

        # 1. 预留点位，列为空 (忽略)
        context_reserved = self._create_context({
            C.HMI_NAME_COL: np.nan, # 预留
            C.POWER_SUPPLY_TYPE_COL: None
        })
        self.assertEqual(rule.validate(context_reserved), [], "预留点位不应触发此规则")

        # 2. 非预留点位，列有值 (有效)
        context_non_reserved_filled = self._create_context({
            C.HMI_NAME_COL: "Tag1", # 非预留
            C.POWER_SUPPLY_TYPE_COL: C.ALLOWED_POWER_SUPPLY_VALUES[0]
        })
        self.assertEqual(rule.validate(context_non_reserved_filled), [], "非预留点位且列有值时应无错误")

        # 3. 非预留点位，列为空 (无效)
        context_non_reserved_empty = self._create_context({
            C.HMI_NAME_COL: "Tag1", # 非预留
            C.POWER_SUPPLY_TYPE_COL: ""
        })
        errors = rule.validate(context_non_reserved_empty)
        self.assertEqual(len(errors), 1, "非预留点位且列为空时应有1个错误")
        self.assertHasError(errors, "此列必填")
        self.assertHasError(errors, f'"{C.POWER_SUPPLY_TYPE_COL}"')

    def test_power_supply_value_rule(self):
        """测试非预留点位供电类型值有效性规则。"""
        rule = PowerSupplyValueRule()

        # 1. 预留点位 (忽略)
        context_reserved = self._create_context({
            C.HMI_NAME_COL: np.nan, # 预留
            C.POWER_SUPPLY_TYPE_COL: "无效值"
        })
        self.assertEqual(rule.validate(context_reserved), [], "预留点位不应触发此规则")

        # 2. 非预留点位，值有效 (有效)
        context_valid = self._create_context({
            C.HMI_NAME_COL: "Tag1", # 非预留
            C.POWER_SUPPLY_TYPE_COL: C.ALLOWED_POWER_SUPPLY_VALUES[0] # 有效值
        })
        self.assertEqual(rule.validate(context_valid), [], "非预留点位且值有效时应无错误")

        # 3. 非预留点位，值无效 (无效)
        invalid_value = "无效值"
        context_invalid = self._create_context({
            C.HMI_NAME_COL: "Tag1", # 非预留
            C.POWER_SUPPLY_TYPE_COL: invalid_value
        })
        errors = rule.validate(context_invalid)
        self.assertEqual(len(errors), 1, "非预留点位且值无效时应有1个错误")
        self.assertHasError(errors, "的值无效")
        self.assertHasError(errors, f'"{C.POWER_SUPPLY_TYPE_COL}"')
        self.assertHasError(errors, ", ".join(C.ALLOWED_POWER_SUPPLY_VALUES))

        # 4. 非预留点位，值为空 (有效，由 NonReservedRequiredRule 处理必填)
        context_empty = self._create_context({
            C.HMI_NAME_COL: "Tag1", # 非预留
            C.POWER_SUPPLY_TYPE_COL: None
        })
        self.assertEqual(rule.validate(context_empty), [], "非预留点位但值为空时，此规则不报错")

    def test_wiring_system_value_rule(self):
        """测试非预留点位线制值有效性规则（区分模块类型）。"""
        rule = WiringSystemValueRule()

        # 1. 预留点位 (忽略)
        context_reserved = self._create_context({
            C.HMI_NAME_COL: np.nan, C.WIRING_SYSTEM_COL: "无效值", C.MODULE_TYPE_COL: C.MODULE_TYPE_AI
        })
        self.assertEqual(rule.validate(context_reserved), [], "预留点位不应触发此规则")

        # 2. 非预留，AI 模块，有效值 (有效)
        context_ai_valid = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.WIRING_SYSTEM_COL: C.ALLOWED_WIRING_SYSTEM_VALUES_AI_AO[0],
            C.MODULE_TYPE_COL: C.MODULE_TYPE_AI
        })
        self.assertEqual(rule.validate(context_ai_valid), [], "非预留AI，有效线制")

        # 3. 非预留，AI 模块，无效值 (无效)
        context_ai_invalid = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.WIRING_SYSTEM_COL: C.ALLOWED_WIRING_SYSTEM_VALUES_DI_DO[0], # 用 DI/DO 的值
            C.MODULE_TYPE_COL: C.MODULE_TYPE_AI
        })
        errors_ai_invalid = rule.validate(context_ai_invalid)
        self.assertEqual(len(errors_ai_invalid), 1, "非预留AI，无效线制")
        self.assertHasError(errors_ai_invalid, "对AI/AO模块无效")
        self.assertHasError(errors_ai_invalid, C.ALLOWED_WIRING_SYSTEM_VALUES_AI_AO[0])

        # 4. 非预留，DI 模块，有效值 (有效)
        context_di_valid = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.WIRING_SYSTEM_COL: C.ALLOWED_WIRING_SYSTEM_VALUES_DI_DO[0],
            C.MODULE_TYPE_COL: C.MODULE_TYPE_DI
        })
        self.assertEqual(rule.validate(context_di_valid), [], "非预留DI，有效线制")

        # 5. 非预留，DI 模块，无效值 (无效)
        context_di_invalid = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.WIRING_SYSTEM_COL: C.ALLOWED_WIRING_SYSTEM_VALUES_AI_AO[0], # 用 AI/AO 的值
            C.MODULE_TYPE_COL: C.MODULE_TYPE_DI
        })
        errors_di_invalid = rule.validate(context_di_invalid)
        self.assertEqual(len(errors_di_invalid), 1, "非预留DI，无效线制")
        self.assertHasError(errors_di_invalid, "对DI/DO模块无效")
        self.assertHasError(errors_di_invalid, C.ALLOWED_WIRING_SYSTEM_VALUES_DI_DO[0])

        # 6. 非预留，未知模块类型 (报错)
        context_unknown_module = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.WIRING_SYSTEM_COL: C.ALLOWED_WIRING_SYSTEM_VALUES_AI_AO[0],
            C.MODULE_TYPE_COL: ""
        })
        errors_unknown = rule.validate(context_unknown_module)
        self.assertEqual(len(errors_unknown), 1, "非预留，未知模块类型")
        self.assertHasError(errors_unknown, "无法确定")
        self.assertHasError(errors_unknown, f'"{C.MODULE_TYPE_COL}"为空')

        # 7. 非预留，其他模块类型 (忽略)
        context_other_module = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.WIRING_SYSTEM_COL: "任何值", C.MODULE_TYPE_COL: "OTHER"
        })
        self.assertEqual(rule.validate(context_other_module), [], "非预留，其他模块类型，忽略线制校验")

        # 8. 非预留，线制为空 (有效，由 NonReservedRequiredRule 处理必填)
        context_empty = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.WIRING_SYSTEM_COL: None, C.MODULE_TYPE_COL: C.MODULE_TYPE_AI
        })
        self.assertEqual(rule.validate(context_empty), [], "非预留但线制为空时，此规则不报错")

    def test_range_required_ai_rule(self):
        """测试非预留AI模块量程必填规则。"""
        rule = RangeRequiredAiRule()

        # 1. 预留点位 (忽略)
        context_reserved = self._create_context({C.HMI_NAME_COL: np.nan, C.MODULE_TYPE_COL: C.MODULE_TYPE_AI})
        self.assertEqual(rule.validate(context_reserved), [], "预留点位忽略")

        # 2. 非 AI 模块 (忽略)
        context_not_ai = self._create_context({C.HMI_NAME_COL: "Tag1", C.MODULE_TYPE_COL: C.MODULE_TYPE_DI})
        self.assertEqual(rule.validate(context_not_ai), [], "非 AI 模块忽略")

        # 3. 非预留 AI，量程都填写 (有效)
        context_valid = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.MODULE_TYPE_COL: C.MODULE_TYPE_AI,
            C.RANGE_LOW_LIMIT_COL: 0, C.RANGE_HIGH_LIMIT_COL: 100
        })
        self.assertEqual(rule.validate(context_valid), [], "非预留 AI，量程都填写")

        # 4. 非预留 AI，低限为空 (无效)
        context_low_empty = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.MODULE_TYPE_COL: C.MODULE_TYPE_AI,
            C.RANGE_LOW_LIMIT_COL: None, C.RANGE_HIGH_LIMIT_COL: 100
        })
        errors_low = rule.validate(context_low_empty)
        self.assertEqual(len(errors_low), 1, "非预留 AI，低限为空")
        self.assertHasError(errors_low, f'"{C.RANGE_LOW_LIMIT_COL}"为空')

        # 5. 非预留 AI，高限为空 (无效)
        context_high_empty = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.MODULE_TYPE_COL: C.MODULE_TYPE_AI,
            C.RANGE_LOW_LIMIT_COL: 0, C.RANGE_HIGH_LIMIT_COL: ""
        })
        errors_high = rule.validate(context_high_empty)
        self.assertEqual(len(errors_high), 1, "非预留 AI，高限为空")
        self.assertHasError(errors_high, f'"{C.RANGE_HIGH_LIMIT_COL}"为空')

        # 6. 非预留 AI，两者都为空 (无效)
        context_both_empty = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.MODULE_TYPE_COL: C.MODULE_TYPE_AI,
            C.RANGE_LOW_LIMIT_COL: np.nan, C.RANGE_HIGH_LIMIT_COL: None
        })
        errors_both = rule.validate(context_both_empty)
        self.assertEqual(len(errors_both), 2, "非预留 AI，两者都为空")
        self.assertHasError(errors_both, f'"{C.RANGE_LOW_LIMIT_COL}"为空')
        self.assertHasError(errors_both, f'"{C.RANGE_HIGH_LIMIT_COL}"为空')

    def test_range_numeric_ai_rule(self):
        """测试非预留AI模块量程数字校验规则。"""
        rule_low = RangeNumericAiRule(C.RANGE_LOW_LIMIT_COL, "量程低限")
        rule_high = RangeNumericAiRule(C.RANGE_HIGH_LIMIT_COL, "量程高限")

        # 1. 预留点位 (忽略)
        context_reserved = self._create_context({C.HMI_NAME_COL: np.nan, C.MODULE_TYPE_COL: C.MODULE_TYPE_AI, C.RANGE_LOW_LIMIT_COL: "abc"})
        self.assertEqual(rule_low.validate(context_reserved), [], "预留点位忽略")

        # 2. 非 AI 模块 (忽略)
        context_not_ai = self._create_context({C.HMI_NAME_COL: "Tag1", C.MODULE_TYPE_COL: C.MODULE_TYPE_DI, C.RANGE_LOW_LIMIT_COL: "abc"})
        self.assertEqual(rule_low.validate(context_not_ai), [], "非 AI 模块忽略")

        # 3. 非预留 AI，值为数字 (有效)
        context_numeric = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.MODULE_TYPE_COL: C.MODULE_TYPE_AI,
            C.RANGE_LOW_LIMIT_COL: 0, C.RANGE_HIGH_LIMIT_COL: 100.5
        })
        self.assertEqual(rule_low.validate(context_numeric), [], "非预留 AI，低限数字")
        self.assertEqual(rule_high.validate(context_numeric), [], "非预留 AI，高限数字")

        # 4. 非预留 AI，值非数字 (无效)
        context_non_numeric = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.MODULE_TYPE_COL: C.MODULE_TYPE_AI,
            C.RANGE_LOW_LIMIT_COL: "abc", C.RANGE_HIGH_LIMIT_COL: True # 布尔也不是数字
        })
        errors_low = rule_low.validate(context_non_numeric)
        errors_high = rule_high.validate(context_non_numeric)
        self.assertEqual(len(errors_low), 1, "非预留 AI，低限非数字")
        self.assertHasError(errors_low, "必须为整数或小数")
        self.assertHasError(errors_low, f'"{C.RANGE_LOW_LIMIT_COL}"')
        self.assertEqual(len(errors_high), 1, "非预留 AI，高限非数字")
        self.assertHasError(errors_high, "必须为整数或小数")
        self.assertHasError(errors_high, f'"{C.RANGE_HIGH_LIMIT_COL}"')

        # 5. 非预留 AI，值为空 (有效，此规则不检查空值)
        context_empty = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.MODULE_TYPE_COL: C.MODULE_TYPE_AI,
            C.RANGE_LOW_LIMIT_COL: None
        })
        self.assertEqual(rule_low.validate(context_empty), [], "非预留 AI，低限为空，此规则忽略")

    def test_setpoint_numeric_ai_rule(self):
        """测试非预留AI模块设定值数字校验规则。"""
        rule = SetpointNumericAiRule(C.SLL_SET_COL, "SLL设定值") # 以 SLL 为例

        # 1. 预留点位 (忽略)
        context_reserved = self._create_context({C.HMI_NAME_COL: np.nan, C.MODULE_TYPE_COL: C.MODULE_TYPE_AI, C.SLL_SET_COL: "abc"})
        self.assertEqual(rule.validate(context_reserved), [], "预留点位忽略")

        # 2. 非 AI 模块 (忽略)
        context_not_ai = self._create_context({C.HMI_NAME_COL: "Tag1", C.MODULE_TYPE_COL: C.MODULE_TYPE_DI, C.SLL_SET_COL: "abc"})
        self.assertEqual(rule.validate(context_not_ai), [], "非 AI 模块忽略")

        # 3. 非预留 AI，值为数字 (有效)
        context_numeric = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.MODULE_TYPE_COL: C.MODULE_TYPE_AI, C.SLL_SET_COL: -10.5
        })
        self.assertEqual(rule.validate(context_numeric), [], "非预留 AI，设定值数字")

        # 4. 非预留 AI，值非数字 (无效)
        context_non_numeric = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.MODULE_TYPE_COL: C.MODULE_TYPE_AI, C.SLL_SET_COL: "text"
        })
        errors = rule.validate(context_non_numeric)
        self.assertEqual(len(errors), 1, "非预留 AI，设定值非数字")
        self.assertHasError(errors, "必须为整数或小数")
        self.assertHasError(errors, f'"{C.SLL_SET_COL}"')

        # 5. 非预留 AI，值为空 (有效，此规则不检查空值)
        context_empty = self._create_context({
            C.HMI_NAME_COL: "Tag1", C.MODULE_TYPE_COL: C.MODULE_TYPE_AI, C.SLL_SET_COL: None
        })
        self.assertEqual(rule.validate(context_empty), [], "非预留 AI，设定值为空，此规则忽略")

    def test_reserved_ai_specific_empty_rule(self):
        """测试预留AI模块量程/设定值为空规则。"""
        rule_range = ReservedAiSpecificEmptyRule(C.RANGE_LOW_LIMIT_COL, "量程低限")
        rule_setpoint = ReservedAiSpecificEmptyRule(C.SLL_SET_COL, "SLL设定值")

        # 1. 非预留点位 (忽略)
        context_non_reserved = self._create_context({C.HMI_NAME_COL: "Tag1", C.MODULE_TYPE_COL: C.MODULE_TYPE_AI, C.RANGE_LOW_LIMIT_COL: 0})
        self.assertEqual(rule_range.validate(context_non_reserved), [], "非预留点位忽略")

        # 2. 非 AI 模块 (忽略)
        context_not_ai = self._create_context({C.HMI_NAME_COL: np.nan, C.MODULE_TYPE_COL: C.MODULE_TYPE_DI, C.RANGE_LOW_LIMIT_COL: 0})
        self.assertEqual(rule_range.validate(context_not_ai), [], "非 AI 模块忽略")

        # 3. 预留 AI，相关列为空 (有效)
        context_empty = self._create_context({
            C.HMI_NAME_COL: np.nan, C.MODULE_TYPE_COL: C.MODULE_TYPE_AI,
            C.RANGE_LOW_LIMIT_COL: None, C.SLL_SET_COL: np.nan
        })
        self.assertEqual(rule_range.validate(context_empty), [], "预留 AI，量程为空")
        self.assertEqual(rule_setpoint.validate(context_empty), [], "预留 AI，设定值为空")

        # 4. 预留 AI，相关列有值 (无效)
        context_filled = self._create_context({
            C.HMI_NAME_COL: None, C.MODULE_TYPE_COL: C.MODULE_TYPE_AI,
            C.RANGE_LOW_LIMIT_COL: 0, C.SLL_SET_COL: 10
        })
        errors_range = rule_range.validate(context_filled)
        errors_setpoint = rule_setpoint.validate(context_filled)
        self.assertEqual(len(errors_range), 1, "预留 AI，量程有值")
        self.assertHasError(errors_range, "预留点位的此列必须为空")
        self.assertHasError(errors_range, f'"{C.RANGE_LOW_LIMIT_COL}"')
        self.assertEqual(len(errors_setpoint), 1, "预留 AI，设定值有值")
        self.assertHasError(errors_setpoint, "预留点位的此列必须为空")
        self.assertHasError(errors_setpoint, f'"{C.SLL_SET_COL}"')

    def test_real_setpoint_uniqueness_rule(self):
        """测试第三方表 REAL 类型设定值唯一性规则。"""
        rule = RealSetpointUniquenessRule()

        # 1. 数据类型不是 REAL (忽略)
        context_not_real = self._create_context({
            C.TP_INPUT_DATA_TYPE_COL: "BOOL",
            C.TP_INPUT_SLL_SET_COL: 10, C.TP_INPUT_SL_SET_COL: 20
        })
        self.assertEqual(rule.validate(context_not_real), [], "非 REAL 类型忽略")

        # 2. REAL 类型，没有设定值 (有效)
        context_real_no_setpoints = self._create_context({
            C.TP_INPUT_DATA_TYPE_COL: C.DATA_TYPE_REAL
        })
        self.assertEqual(rule.validate(context_real_no_setpoints), [], "REAL 类型，无设定值")

        # 3. REAL 类型，只有一个设定值 (有效)
        context_real_one_setpoint = self._create_context({
            C.TP_INPUT_DATA_TYPE_COL: C.DATA_TYPE_REAL,
            C.TP_INPUT_SH_SET_COL: 80.5
        })
        self.assertEqual(rule.validate(context_real_one_setpoint), [], "REAL 类型，一个设定值")

        # 4. REAL 类型，有多个设定值 (无效)
        context_real_multiple_setpoints = self._create_context({
            C.TP_INPUT_DATA_TYPE_COL: C.DATA_TYPE_REAL,
            C.TP_INPUT_SL_SET_COL: 20,
            C.TP_INPUT_SH_SET_COL: 80,
            C.TP_INPUT_VAR_NAME_COL: "TestVar"
        })
        errors = rule.validate(context_real_multiple_setpoints)
        self.assertEqual(len(errors), 1, "REAL 类型，多个设定值")
        self.assertHasError(errors, "存在多个有效值")
        self.assertHasError(errors, f"{C.TP_INPUT_SL_SET_COL}='20'")
        self.assertHasError(errors, f"{C.TP_INPUT_SH_SET_COL}='80'")
        self.assertHasError(errors, "TestVar") # 检查点位名称是否包含在错误中

        # 5. REAL 类型，有多个设定值，但部分是空字符串或 NaN (有效，只有一个有效值)
        context_real_mixed_presence = self._create_context({
            C.TP_INPUT_DATA_TYPE_COL: C.DATA_TYPE_REAL,
            C.TP_INPUT_SL_SET_COL: "",
            C.TP_INPUT_SH_SET_COL: 90,
            C.TP_INPUT_SHH_SET_COL: np.nan,
            C.TP_INPUT_VAR_NAME_COL: "MixedVar"
        })
        self.assertEqual(rule.validate(context_real_mixed_presence), [], "REAL 类型，只有一个有效设定值")

    def test_bool_setpoint_empty_rule(self):
        """测试 BOOL 类型点位设定值必须为空的规则。"""
        rule = BoolSetpointEmptyRule()

        # 1. 数据类型不是 BOOL (忽略)
        context_not_bool = self._create_context({
            C.TP_INPUT_DATA_TYPE_COL: C.DATA_TYPE_REAL,
            C.TP_INPUT_SLL_SET_COL: 10 # 即使有值也忽略
        })
        self.assertEqual(rule.validate(context_not_bool), [], "非 BOOL 类型忽略")

        # 2. BOOL 类型，设定值都为空 (有效)
        context_bool_empty = self._create_context({
            C.TP_INPUT_VAR_NAME_COL: "BoolValid",
            C.TP_INPUT_DATA_TYPE_COL: C.DATA_TYPE_BOOL,
            C.TP_INPUT_SLL_SET_COL: None,
            C.TP_INPUT_SL_SET_COL: np.nan,
            C.TP_INPUT_SH_SET_COL: "",
            C.TP_INPUT_SHH_SET_COL: None
        })
        self.assertEqual(rule.validate(context_bool_empty), [], "BOOL 类型，设定值为空")

        # 3. BOOL 类型，SLL 设定值非空 (无效)
        context_bool_sll_filled = self._create_context({
            C.TP_INPUT_VAR_NAME_COL: "BoolInvalidSLL",
            C.TP_INPUT_DATA_TYPE_COL: C.DATA_TYPE_BOOL,
            C.TP_INPUT_SLL_SET_COL: 0 # 即使是 0 也算有值
        })
        errors_sll = rule.validate(context_bool_sll_filled)
        self.assertEqual(len(errors_sll), 1, "BOOL 类型，SLL 有值")
        self.assertHasError(errors_sll, "不应填写数据")
        self.assertHasError(errors_sll, f'"{C.TP_INPUT_SLL_SET_COL}"')
        self.assertHasError(errors_sll, "BoolInvalidSLL")

        # 4. BOOL 类型，多个设定值非空 (无效)
        context_bool_multiple_filled = self._create_context({
            C.TP_INPUT_VAR_NAME_COL: "BoolInvalidMultiple",
            C.TP_INPUT_DATA_TYPE_COL: C.DATA_TYPE_BOOL,
            C.TP_INPUT_SL_SET_COL: 1,
            C.TP_INPUT_SHH_SET_COL: "True"
        })
        errors_multiple = rule.validate(context_bool_multiple_filled)
        self.assertEqual(len(errors_multiple), 2, "BOOL 类型，多个设定值有值")
        # 检查是否对 SL 和 SHH 都报了错
        self.assertTrue(any(f'"{C.TP_INPUT_SL_SET_COL}"' in e for e in errors_multiple), "应包含 SL 的错误")
        self.assertTrue(any(f'"{C.TP_INPUT_SHH_SET_COL}"' in e for e in errors_multiple), "应包含 SHH 的错误")
        self.assertHasError(errors_multiple, "不应填写数据") # 检查通用错误信息
        self.assertHasError(errors_multiple, "BoolInvalidMultiple") # 检查点位名称

    def test_hmi_name_uniqueness_rule(self):
        """测试主IO点表HMI名称唯一性校验。"""
        df = pd.DataFrame({
            C.HMI_NAME_COL: ["A", "B", "C", "A", None, "  ", "D"],
            C.DESCRIPTION_COL: ["a", "b", "c", "d", "e", "f", "g"]
        })
        # 行号应为2,3,4,5,6,7,8
        sheet_name = "IO点表"
        rule = HmiNameUniquenessRule()
        errors = rule.validate_sheet(df, sheet_name)
        self.assertEqual(len(errors), 1, "有重复HMI时应有1个报错")
        self.assertIn('变量名 "A"', errors[0])
        self.assertIn('2', errors[0])
        self.assertIn('5', errors[0])
        # 唯一时无报错
        df2 = pd.DataFrame({C.HMI_NAME_COL: ["A", "B", "C", None, "  ", "D"]})
        errors2 = rule.validate_sheet(df2, sheet_name)
        self.assertEqual(errors2, [], "所有HMI唯一时应无报错")

# --- 添加更多测试用例的地方 ---

# --- 测试入口函数 (集成测试) ---

class TestValidateIoTableIntegration(unittest.TestCase):

    def setUp(self):
        """在每个测试前创建临时目录。"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """在每个测试后删除临时目录及其内容，增加重试逻辑处理 PermissionError。"""
        attempts = 3
        delay = 0.1 # seconds
        for i in range(attempts):
            try:
                shutil.rmtree(self.test_dir)
                break # Success
            except PermissionError as e:
                if i < attempts - 1:
                    print(f"\nWarning: PermissionError on teardown deleting {self.test_dir}, retrying in {delay}s...")
                    import time
                    time.sleep(delay)
                    delay *= 2 # Optional: increase delay
                else:
                    print(f"\nError: Failed to remove temp dir {self.test_dir} after {attempts} attempts: {e}")
                    # Depending on CI/environment, you might want to raise the error
                    # raise e
            except Exception as e:
                # Handle other potential errors during cleanup
                print(f"\nError during teardown of {self.test_dir}: {e}")
                break

    def _create_excel_file(self, filename: str, sheet_data: dict) -> str:
        """辅助函数：在临时目录中创建 Excel 文件。"""
        file_path = os.path.join(self.test_dir, filename)
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            for sheet_name, df_data in sheet_data.items():
                 # 如果 df_data 是字典列表，先转为 DataFrame
                if isinstance(df_data, list):
                    # 需要知道列的顺序和完整性，最好传入 DataFrame
                    # 为了简单起见，假设列完整
                    df = pd.DataFrame(df_data)
                elif isinstance(df_data, pd.DataFrame):
                    df = df_data
                else:
                    raise TypeError("sheet_data 的值必须是 DataFrame 或字典列表")
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        return file_path

    def test_valid_file(self):
        """测试一个完全有效的 Excel 文件。"""
        main_sheet_cols = [
            C.HMI_NAME_COL, C.DESCRIPTION_COL, C.POWER_SUPPLY_TYPE_COL, C.WIRING_SYSTEM_COL,
            C.MODULE_TYPE_COL, C.RANGE_LOW_LIMIT_COL, C.RANGE_HIGH_LIMIT_COL,
            C.SLL_SET_COL, C.SL_SET_COL, C.SH_SET_COL, C.SHH_SET_COL
        ]
        tp_sheet_cols = [
             C.TP_INPUT_VAR_NAME_COL, C.TP_INPUT_DATA_TYPE_COL,
            C.TP_INPUT_SLL_SET_COL, C.TP_INPUT_SL_SET_COL,
            C.TP_INPUT_SH_SET_COL, C.TP_INPUT_SHH_SET_COL
        ]

        valid_main_data = pd.DataFrame([
            {
                C.HMI_NAME_COL: "AI_Valid", C.DESCRIPTION_COL: "Desc",
                C.POWER_SUPPLY_TYPE_COL: C.ALLOWED_POWER_SUPPLY_VALUES[0],
                C.WIRING_SYSTEM_COL: C.ALLOWED_WIRING_SYSTEM_VALUES_AI_AO[0],
                C.MODULE_TYPE_COL: C.MODULE_TYPE_AI,
                C.RANGE_LOW_LIMIT_COL: 0, C.RANGE_HIGH_LIMIT_COL: 100
            }
        ]).reindex(columns=main_sheet_cols)

        valid_tp_data = pd.DataFrame([
             {
                C.TP_INPUT_VAR_NAME_COL: "TP_Valid",
                C.TP_INPUT_DATA_TYPE_COL: C.DATA_TYPE_REAL,
                C.TP_INPUT_SH_SET_COL: 100
            }
        ]).reindex(columns=tp_sheet_cols)

        sheet_data = {
            C.PLC_IO_SHEET_NAME: valid_main_data,
            "ThirdPartySheet1": valid_tp_data
        }
        file_path = self._create_excel_file("valid.xlsx", sheet_data)
        is_valid, message = validate_io_table(file_path)
        self.assertTrue(is_valid, f"有效文件校验失败: {message}")
        self.assertIn("验证通过", message)

    def test_file_with_errors(self):
        """测试包含错误的 Excel 文件。"""
        # 复用 TestSheetValidation 中的错误数据
        main_sheet_cols = [
            C.HMI_NAME_COL, C.DESCRIPTION_COL, C.POWER_SUPPLY_TYPE_COL, C.WIRING_SYSTEM_COL,
            C.MODULE_TYPE_COL, C.RANGE_LOW_LIMIT_COL, C.RANGE_HIGH_LIMIT_COL,
            C.SLL_SET_COL, C.SL_SET_COL, C.SH_SET_COL, C.SHH_SET_COL
        ]
        tp_sheet_cols = [
             C.TP_INPUT_VAR_NAME_COL, C.TP_INPUT_DATA_TYPE_COL,
            C.TP_INPUT_SLL_SET_COL, C.TP_INPUT_SL_SET_COL,
            C.TP_INPUT_SH_SET_COL, C.TP_INPUT_SHH_SET_COL
        ]
        invalid_main_data = [
             { # 无效行 1: 预留点位，POWER_SUPPLY_TYPE_COL 为空 (np.nan 默认)
                C.HMI_NAME_COL: np.nan, C.DESCRIPTION_COL: None,
                # POWER_SUPPLY_TYPE_COL 将默认为 np.nan
                C.WIRING_SYSTEM_COL: C.ALLOWED_WIRING_SYSTEM_VALUES_AI_AO[0], # 给线制一个有效值，避免它也报错
                C.MODULE_TYPE_COL: C.MODULE_TYPE_AI,
            },
        ]
        invalid_tp_data = [
            { # 无效 REAL 行 (多个设定值)
                C.TP_INPUT_VAR_NAME_COL: "TP_Invalid",
                C.TP_INPUT_DATA_TYPE_COL: C.DATA_TYPE_REAL,
                C.TP_INPUT_SLL_SET_COL: 10,
                C.TP_INPUT_SL_SET_COL: 20
            },
        ]
        df_main_invalid = pd.DataFrame(invalid_main_data).reindex(columns=main_sheet_cols)
        df_tp_invalid = pd.DataFrame(invalid_tp_data).reindex(columns=tp_sheet_cols)

        sheet_data = {
            C.PLC_IO_SHEET_NAME: df_main_invalid,
            "ThirdPartyErrors": df_tp_invalid
        }
        file_path = self._create_excel_file("errors.xlsx", sheet_data)
        is_valid, message = validate_io_table(file_path)
        self.assertFalse(is_valid, "包含错误的文件应校验失败")
        
        # 验证主表错误：POWER_SUPPLY_TYPE_COL 因 AlwaysRequiredRule 而报错
        self.assertIn(f'列 "{C.POWER_SUPPLY_TYPE_COL}" 是必填项，不能为空。', message)
        self.assertIn(f'工作表:"{C.PLC_IO_SHEET_NAME}", Excel行号:2', message) # 预留错误行号 index 0 + 2
        
        # 验证第三方表错误
        self.assertIn("存在多个有效值", message) 
        self.assertIn("TP_Invalid", message)
        self.assertIn(f'工作表:"ThirdPartyErrors", Excel行号:2', message)

    def test_missing_main_sheet(self):
        """测试缺少主 IO 点表的情况。"""
        tp_sheet_cols = [
             C.TP_INPUT_VAR_NAME_COL, C.TP_INPUT_DATA_TYPE_COL,
            C.TP_INPUT_SLL_SET_COL, C.TP_INPUT_SL_SET_COL,
            C.TP_INPUT_SH_SET_COL, C.TP_INPUT_SHH_SET_COL
        ]
        valid_tp_data = pd.DataFrame([
             {
                C.TP_INPUT_VAR_NAME_COL: "TP_Valid",
                C.TP_INPUT_DATA_TYPE_COL: "BOOL"
            }
        ]).reindex(columns=tp_sheet_cols)
        sheet_data = {
            "SomeOtherSheet": valid_tp_data
        }
        file_path = self._create_excel_file("no_main.xlsx", sheet_data)
        is_valid, message = validate_io_table(file_path)
        # 缺少主表不算致命错误，但应包含警告信息
        self.assertFalse(is_valid, "缺少主表时，is_valid 应为 False 或根据实际业务调整") # 或者 True? 取决于业务定义
        self.assertIn(f'未找到强制要求的主工作表"{C.PLC_IO_SHEET_NAME}"' , message)

    def test_file_not_found(self):
        """测试文件不存在的情况。"""
        non_existent_path = os.path.join(self.test_dir, "not_a_real_file.xlsx")
        is_valid, message = validate_io_table(non_existent_path)
        self.assertFalse(is_valid)
        self.assertIn("文件未找到", message)

    def test_invalid_format_not_excel(self):
        """测试非 Excel 文件。"""
        file_path = os.path.join(self.test_dir, "invalid.txt")
        with open(file_path, "w") as f:
            f.write("This is not an excel file.")
        is_valid, message = validate_io_table(file_path)
        self.assertFalse(is_valid)
        self.assertIn("文件格式无效", message)

    def test_empty_excel_file(self):
        """测试包含空Sheet的Excel文件。"""
        file_path = os.path.join(self.test_dir, "empty_sheet.xlsx")
        # 创建一个包含单个空Sheet的文件
        empty_df = pd.DataFrame()
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
             empty_df.to_excel(writer, sheet_name="EmptySheet", index=False)
        # 'with' statement handles closing the writer

        is_valid, message = validate_io_table(file_path)
        # 预期：文件可打开，空 sheet 被跳过，最终报告找不到主 sheet
        self.assertFalse(is_valid, "包含空Sheet且无主Sheet的文件应校验失败")
        self.assertIn(f'未找到强制要求的主工作表"{C.PLC_IO_SHEET_NAME}"' , message)
        self.assertNotIn("不包含任何工作表", message, "不应报告'不包含任何工作表'")

class TestAlwaysRequiredRule(unittest.TestCase):
    """测试 AlwaysRequiredRule 的行为"""

    def _create_context(self, data: dict, sheet_name=TEST_SHEET_NAME, row_num=TEST_EXCEL_ROW_NUM) -> ValidationContext:
        """辅助函数：根据字典创建测试用的 ValidationContext。"""
        # 确保所有可能的列都存在，即使值为 None 或 NaN
        all_cols = [
            C.HMI_NAME_COL, C.DESCRIPTION_COL, C.POWER_SUPPLY_TYPE_COL,
            C.WIRING_SYSTEM_COL, C.MODULE_TYPE_COL
        ]
        full_data = {col: data.get(col, np.nan) for col in all_cols}
        row = pd.Series(full_data)
        return ValidationContext(row, row_num, sheet_name)

    def assertHasError(self, errors: list, substring: str):
        """断言错误列表中包含特定子字符串。"""
        self.assertTrue(any(substring in error for error in errors),
                        f"错误列表中未找到包含 '{substring}' 的错误。错误列表: {errors}")

    def test_power_supply_type_required(self):
        """测试供电类型列必填规则"""
        rule = AlwaysRequiredRule(C.POWER_SUPPLY_TYPE_COL, "供电类型（有源/无源）")

        # 1. 供电类型为空（无效）
        context_empty = self._create_context({
            C.HMI_NAME_COL: "Tag1",
            C.POWER_SUPPLY_TYPE_COL: None
        })
        errors = rule.validate(context_empty)
        self.assertEqual(len(errors), 1, "供电类型为空时应有1个错误")
        self.assertHasError(errors, "是必填项，不能为空")
        self.assertHasError(errors, f'"{C.POWER_SUPPLY_TYPE_COL}"')

        # 2. 供电类型填写正确（有效）
        context_valid = self._create_context({
            C.HMI_NAME_COL: "Tag1",
            C.POWER_SUPPLY_TYPE_COL: C.ALLOWED_POWER_SUPPLY_VALUES[0]
        })
        self.assertEqual(rule.validate(context_valid), [], "供电类型填写正确时应无错误")

        # 3. 供电类型填写错误（有效 - 值有效性由 PowerSupplyValueRule 处理）
        context_invalid_value = self._create_context({
            C.HMI_NAME_COL: "Tag1",
            C.POWER_SUPPLY_TYPE_COL: "无效值"
        })
        self.assertEqual(rule.validate(context_invalid_value), [], "供电类型填写错误时，此规则不报错")

    def test_wiring_system_required(self):
        """测试线制列必填规则"""
        rule = AlwaysRequiredRule(C.WIRING_SYSTEM_COL, "线制")

        # 1. 线制为空（无效）
        context_empty = self._create_context({
            C.HMI_NAME_COL: "Tag1",
            C.WIRING_SYSTEM_COL: None,
            C.MODULE_TYPE_COL: C.MODULE_TYPE_AI
        })
        errors = rule.validate(context_empty)
        self.assertEqual(len(errors), 1, "线制为空时应有1个错误")
        self.assertHasError(errors, "是必填项，不能为空")
        self.assertHasError(errors, f'"{C.WIRING_SYSTEM_COL}"')

        # 2. 线制填写正确（有效）
        context_valid = self._create_context({
            C.HMI_NAME_COL: "Tag1",
            C.WIRING_SYSTEM_COL: C.ALLOWED_WIRING_SYSTEM_VALUES_AI_AO[0],
            C.MODULE_TYPE_COL: C.MODULE_TYPE_AI
        })
        self.assertEqual(rule.validate(context_valid), [], "线制填写正确时应无错误")

        # 3. 线制填写错误（有效 - 值有效性由 WiringSystemValueRule 处理）
        context_invalid_value = self._create_context({
            C.HMI_NAME_COL: "Tag1",
            C.WIRING_SYSTEM_COL: "无效值",
            C.MODULE_TYPE_COL: C.MODULE_TYPE_AI
        })
        self.assertEqual(rule.validate(context_invalid_value), [], "线制填写错误时，此规则不报错")

    def test_both_columns_required(self):
        """测试供电类型和线制两列同时必填的情况"""
        power_supply_rule = AlwaysRequiredRule(C.POWER_SUPPLY_TYPE_COL, "供电类型（有源/无源）")
        wiring_system_rule = AlwaysRequiredRule(C.WIRING_SYSTEM_COL, "线制")

        # 1. 两列都为空（无效）
        context_both_empty = self._create_context({
            C.HMI_NAME_COL: "Tag1",
            C.POWER_SUPPLY_TYPE_COL: None,
            C.WIRING_SYSTEM_COL: None,
            C.MODULE_TYPE_COL: C.MODULE_TYPE_AI
        })
        errors_power = power_supply_rule.validate(context_both_empty)
        errors_wiring = wiring_system_rule.validate(context_both_empty)
        self.assertEqual(len(errors_power), 1, "供电类型为空时应有1个错误")
        self.assertEqual(len(errors_wiring), 1, "线制为空时应有1个错误")
        self.assertHasError(errors_power, "是必填项，不能为空")
        self.assertHasError(errors_wiring, "是必填项，不能为空")
        self.assertHasError(errors_power, f'"{C.POWER_SUPPLY_TYPE_COL}"')
        self.assertHasError(errors_wiring, f'"{C.WIRING_SYSTEM_COL}"')

        # 2. 两列都填写正确（有效）
        context_both_valid = self._create_context({
            C.HMI_NAME_COL: "Tag1",
            C.POWER_SUPPLY_TYPE_COL: C.ALLOWED_POWER_SUPPLY_VALUES[0],
            C.WIRING_SYSTEM_COL: C.ALLOWED_WIRING_SYSTEM_VALUES_AI_AO[0],
            C.MODULE_TYPE_COL: C.MODULE_TYPE_AI
        })
        self.assertEqual(power_supply_rule.validate(context_both_valid), [], "供电类型填写正确时应无错误")
        self.assertEqual(wiring_system_rule.validate(context_both_valid), [], "线制填写正确时应无错误")

        # 3. 一列填写正确，一列为空（部分无效）
        context_mixed = self._create_context({
            C.HMI_NAME_COL: "Tag1",
            C.POWER_SUPPLY_TYPE_COL: C.ALLOWED_POWER_SUPPLY_VALUES[0],
            C.WIRING_SYSTEM_COL: None,
            C.MODULE_TYPE_COL: C.MODULE_TYPE_AI
        })
        errors_power = power_supply_rule.validate(context_mixed)
        errors_wiring = wiring_system_rule.validate(context_mixed)
        self.assertEqual(errors_power, [], "供电类型填写正确时应无错误")
        self.assertEqual(len(errors_wiring), 1, "线制为空时应有1个错误")
        self.assertHasError(errors_wiring, "是必填项，不能为空")
        self.assertHasError(errors_wiring, f'"{C.WIRING_SYSTEM_COL}"')

if __name__ == '__main__':
    unittest.main()