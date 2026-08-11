package com.worldengine.extraction;

import static org.assertj.core.api.Assertions.assertThat;

import com.worldengine.extraction.service.ExtractionQualityEvaluator;
import org.junit.jupiter.api.Test;

class ExtractionQualityEvaluatorTest {

    private final ExtractionQualityEvaluator evaluator = new ExtractionQualityEvaluator(50);

    @Test
    void rejectsNullContent() {
        assertThat(evaluator.isValid(null)).isFalse();
    }

    @Test
    void rejectsContentShorterThanMinLength() {
        assertThat(evaluator.isValid("국내최초 취업정보회사 - 제로베이스")).isFalse();
    }

    @Test
    void acceptsContentAtOrAboveMinLength() {
        String content = "가".repeat(50);
        assertThat(evaluator.isValid(content)).isTrue();
    }

    @Test
    void rejectsCommerceBoilerplate() {
        String content = "교환 및 반품 주소 - 경기도 남양주시 화도읍 경춘로 지현1길 8 (주)케이엔코리아 물류센터 "
            + "교환안내 - 교환 신청서 작성 후 처음 받으신 상품 그대로 포장 후 택배상자에 동봉합니다. "
            + "CJ대한통운 접수 후 교환하실 상품을 착불로 보냅니다. 배송비는 무료배송 대상이 아닙니다. "
            + "쿠폰할인가 적용 시 적립 혜택이 달라질 수 있습니다. 상품번호와 모델번호를 확인해주세요.";
        assertThat(evaluator.isValid(content)).isFalse();
    }

    @Test
    void acceptsRealArticleMentioningFewCommerceWords() {
        String content = "이 프로젝트는 결제 시스템과 배송 추적 기능을 구현한 백엔드 서비스입니다. "
            + "Spring Boot와 JPA를 사용해서 주문 도메인을 설계했고, 테스트 커버리지를 80% 이상 "
            + "유지하는 것을 목표로 했습니다. 아키텍처는 헥사고날 구조를 참고했습니다.";
        assertThat(evaluator.isValid(content)).isTrue();
    }

    @Test
    void rejectsLegalBoilerplate() {
        String content = "이 저작물은 CC BY-NC-SA 2.0 KR에 따라 이용할 수 있습니다. "
            + "기여하신 문서의 저작권은 각 기여자에게 있으며, 각 기여자는 기여하신 부분의 "
            + "저작권을 갖습니다. 나무위키는 백과사전이 아니며 검증되지 않았거나, 편향적이거나, "
            + "잘못된 서술이 있을 수 있습니다.";
        assertThat(evaluator.isValid(content)).isFalse();
    }
}
