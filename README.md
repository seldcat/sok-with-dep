# SoK crawlers with DEP state abstraction

Этот репозиторий содержит кодовую часть экспериментов с краулерами, основанную на проекте [SoK: State of the Krawlers - Evaluating the Effectiveness of Crawling Algorithms for Web Security Measurements](https://www.usenix.org/conference/usenixsecurity24/presentation/stafeev).

Репозиторий не является полным зеркалом оригинального проекта и не предназначен для хранения всех экспериментальных данных. Здесь оставлен код, нужный для работы с краулерами с дополнениями логики по DEP

## Что находится в репозитории

- `crawlers/` - основная кодовая база краулеров из оригинального проекта.
- `arachnarium_examples/` - примеры конфигураций и запусков Arachnarium.
- `experiments/dep/` - добавленная часть для экспериментов с DEP-подходом: конфигурации, скрипты запуска и обработки результатов.

## Оригинальная основа

Большая часть кода сохранена из оригинального проекта State of the Krawlers. Это позволяет использовать уже существующую инфраструктуру Crawljax/Arachnarium и не переписывать базовую логику краулеров с нуля.

## DEP-логика

Дополнительная часть репозитория связана с внедрением DEP-логики в Crawljax state abstraction.

Основные классы находятся в:

```text
crawlers/crawljax/crawljax/examples/src/main/java/com/crawljax/examples/stateabstractions/dep/
```

Ключевые файлы:

- `DepSignature.java` - построение DEP-сигнатуры состояния.
- `DepAwareStateVertex.java` и `DepAwareStateVertexFactory.java` - состояние и фабрика для DEP-aware сравнения.
- `DepOnlyStateVertex.java` и `DepOnlyStateVertexFactory.java` - вариант состояния, основанный только на DEP-сигнатуре.

Интеграция с примером запуска находится в:

```text
crawlers/crawljax/crawljax/examples/src/main/java/com/crawljax/examples/ArachnariumCrawl.java
```

Скрипты и конфигурации для запусков DEP-экспериментов лежат в:

```text
experiments/dep/
```

