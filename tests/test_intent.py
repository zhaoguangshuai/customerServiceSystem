import pytest

from src.agent.intent import Intent, classify_intent, needs_human_handoff


class TestClassifyIntent:
    def test_product_inquiry_gold(self):
        assert classify_intent("你们有黄金项链吗") == Intent.PRODUCT_INQUIRY

    def test_product_inquiry_diamond(self):
        assert classify_intent("想看看钻石戒指") == Intent.PRODUCT_INQUIRY

    def test_product_inquiry_multiple_keywords(self):
        assert classify_intent("18K金手镯和翡翠吊坠") == Intent.PRODUCT_INQUIRY

    def test_price_inquiry(self):
        assert classify_intent("这个项链多少钱") == Intent.PRICE_INQUIRY

    def test_price_inquiry_with_keyword(self):
        assert classify_intent("克价是多少") == Intent.PRICE_INQUIRY

    def test_after_sales(self):
        assert classify_intent("我的戒指需要维修保养") == Intent.AFTER_SALES

    def test_custom_order(self):
        assert classify_intent("可以私人定制吗") == Intent.CUSTOM_ORDER

    def test_complaint(self):
        assert classify_intent("我要投诉，你们的产品是假货") == Intent.COMPLAINT

    def test_price_negotiation(self):
        assert classify_intent("能不能便宜点，给个折扣") == Intent.PRICE_NEGOTIATION

    def test_general_query(self):
        assert classify_intent("你好") == Intent.GENERAL

    def test_empty_query(self):
        assert classify_intent("") == Intent.GENERAL

    def test_highest_score_wins(self):
        # "投诉" and "退货" both match COMPLAINT (2 keywords)
        # "便宜" matches PRICE_NEGOTIATION (1 keyword)
        assert classify_intent("投诉退货便宜") == Intent.COMPLAINT

    def test_mixed_intent_product_wins(self):
        # 3 product keywords vs 1 price keyword
        assert classify_intent("黄金钻石项链价格") == Intent.PRODUCT_INQUIRY


class TestNeedsHumanHandoff:
    def test_complaint_needs_handoff(self):
        assert needs_human_handoff(Intent.COMPLAINT) is True

    def test_price_negotiation_needs_handoff(self):
        assert needs_human_handoff(Intent.PRICE_NEGOTIATION) is True

    def test_custom_order_needs_handoff(self):
        assert needs_human_handoff(Intent.CUSTOM_ORDER) is True

    def test_product_inquiry_no_handoff(self):
        assert needs_human_handoff(Intent.PRODUCT_INQUIRY) is False

    def test_general_no_handoff(self):
        assert needs_human_handoff(Intent.GENERAL) is False

    def test_after_sales_no_handoff(self):
        assert needs_human_handoff(Intent.AFTER_SALES) is False
