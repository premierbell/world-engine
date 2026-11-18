package com.worldengine.common.jpa;

import static org.assertj.core.api.Assertions.assertThat;

import java.sql.Connection;
import java.util.List;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.jdbc.core.JdbcTemplate;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

/**
 * 빈 Postgres에 Flyway 마이그레이션(db/migration)을 처음부터 적용한 뒤, Hibernate validate로 엔티티와 스키마가
 * 맞는지 확인한다. 엔티티에 필드를 추가하고 마이그레이션 파일을 빠뜨리면 컨텍스트가 뜨지 않아 이 테스트가 실패한다.
 *
 * - 기본 테스트(H2)는 Flyway를 끄고 Hibernate가 스키마를 만들기 때문에, 마이그레이션은 여기서만 검증된다.
 * - 실제 DB와 같은 Postgres 18 컨테이너를 쓴다. 시작할 때 이 컨테이너에 붙었는지 확인한다(실제 DB 보호).
 * - Docker가 없으면 건너뛴다(로컬). GitHub Actions에는 Docker가 있어서 CI에서는 항상 돈다.
 */
@Testcontainers(disabledWithoutDocker = true)
@SpringBootTest(properties = {
    "spring.datasource.driver-class-name=org.postgresql.Driver",
    "spring.flyway.enabled=true",
    "spring.jpa.hibernate.ddl-auto=validate"
})
class FlywayMigrationTest {

    @Container
    @ServiceConnection
    static PostgreSQLContainer postgres = new PostgreSQLContainer(DockerImageName.parse("postgres:18.4"));

    @Autowired DataSource dataSource;
    @Autowired JdbcTemplate jdbc;

    @Test
    void 빈_DB에_마이그레이션을_적용하면_엔티티와_스키마가_일치한다() throws Exception {
        try (Connection connection = dataSource.getConnection()) {
            assertThat(connection.getMetaData().getURL())
                .as("반드시 Testcontainers 전용 DB에서만 - 실제 DB 보호")
                .contains(":" + postgres.getMappedPort(5432) + "/" + postgres.getDatabaseName());
        }

        // 여기까지 왔다 = Flyway 적용 성공 + Hibernate validate가 엔티티·스키마 불일치를 찾지 못함
        List<String> applied = jdbc.queryForList(
            "SELECT version FROM flyway_schema_history WHERE success ORDER BY installed_rank", String.class);
        assertThat(applied).first().isEqualTo("1");
    }
}
