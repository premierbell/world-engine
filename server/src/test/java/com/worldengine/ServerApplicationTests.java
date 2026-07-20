package com.worldengine;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * 기본 컨텍스트 로드 스모크 테스트 - src/test/resources/application.properties의
 * H2 인메모리 DB를 쓴다(Docker 불필요). Testcontainers+실제 Postgres 기반
 * 통합 테스트는 실제 JPA 엔티티/리포지토리가 생기는 시점에
 * TestcontainersConfiguration을 따로 @Import해서 추가할 것.
 */
@SpringBootTest
class ServerApplicationTests {

	@Test
	void contextLoads() {
	}

}
