plugins {
	java
	id("org.springframework.boot") version "4.1.0"
	id("io.spring.dependency-management") version "1.1.7"
}

group = "com.worldengine"
version = "0.0.1-SNAPSHOT"
description = "World Engine V1 backend"

java {
	toolchain {
		languageVersion = JavaLanguageVersion.of(21)
	}
}

repositories {
	mavenCentral()
}

dependencies {
	implementation("org.springframework.boot:spring-boot-starter-actuator")
	implementation("org.springframework.boot:spring-boot-starter-data-jpa")
	implementation("org.springframework.boot:spring-boot-starter-validation")
	implementation("org.springframework.boot:spring-boot-starter-webmvc")
	implementation("org.jsoup:jsoup:1.21.1")
	implementation("net.dankito.readability4j:readability4j:1.0.8")
	compileOnly("org.projectlombok:lombok")
	developmentOnly("org.springframework.boot:spring-boot-docker-compose")
	runtimeOnly("org.postgresql:postgresql")
	annotationProcessor("org.projectlombok:lombok")
	testImplementation("org.springframework.boot:spring-boot-starter-actuator-test")
	testImplementation("org.springframework.boot:spring-boot-starter-data-jpa-test")
	testImplementation("org.springframework.boot:spring-boot-starter-validation-test")
	testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")
	testImplementation("org.springframework.boot:spring-boot-testcontainers")
	testImplementation("org.testcontainers:testcontainers-junit-jupiter")
	testImplementation("org.testcontainers:testcontainers-postgresql")
	testImplementation("org.junit.jupiter:junit-jupiter-params")
	testRuntimeOnly("com.h2database:h2")
	testCompileOnly("org.projectlombok:lombok")
	testRuntimeOnly("org.junit.platform:junit-platform-launcher")
	testAnnotationProcessor("org.projectlombok:lombok")
}

// "live" 태그 테스트(실제 네트워크로 외부 URL을 가져오는 테스트, 예:
// ArticleExtractionStrategyLiveTest)는 기본 `test`에서 제외한다 - 외부
// 서비스 상태에 좌우되어 CI/일반 빌드를 불안정하게 만들 수 있다.
// `./gradlew liveTest`로 수동 실행한다.
tasks.test {
	useJUnitPlatform {
		excludeTags("live")
	}
}

tasks.register<Test>("liveTest") {
	description = "실제 네트워크로 외부 URL을 가져오는 'live' 태그 테스트만 실행한다."
	group = "verification"
	useJUnitPlatform {
		includeTags("live")
	}
	testClassesDirs = sourceSets["test"].output.classesDirs
	classpath = sourceSets["test"].runtimeClasspath
	shouldRunAfter(tasks.test)
}
