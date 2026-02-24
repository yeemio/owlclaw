# Implementation Plan: OwlHub (Skills Registry/Hub)

## 文档联动

- requirements: `.kiro/specs/owlhub/requirements.md`
- design: `.kiro/specs/owlhub/design.md`
- tasks: `.kiro/specs/owlhub/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## Overview

This implementation plan breaks down the OwlHub feature into three progressive phases, following the design's architecture evolution from GitHub index mode to static site to service API. Each phase builds on the previous one while maintaining backward compatibility. The plan includes comprehensive testing with both unit tests and property-based tests for all 26 correctness properties.

## Phase 1: GitHub Index Mode (Minimal Viable Registry)

- [x] 1. Set up project structure and core data models
  - Create `owlhub/` package with `indexer/`, `validator/`, and `schema/` subpackages
  - Define `SkillManifest`, `IndexEntry`, `ValidationResult`, `ValidationError` dataclasses in `owlhub/schema/`
  - Define `VersionState` enum (DRAFT, RELEASED, DEPRECATED)
  - Add type hints and docstrings following project conventions
  - _Requirements: 1.1, 1.4, 4.1_

- [x]* 1.1 Write property test for data model serialization
  - **Property 24: GitHub 索引格式正确性**
  - **Validates: Requirements 8.1**
  - Generate random SkillManifest instances and verify JSON serialization matches schema
  - _Requirements: 8.1_

- [x] 2. Implement Validator component
  - [x] 2.1 Create `owlhub/validator/validator.py` with Validator class
    - Implement `validate_version()` with semver regex pattern
    - Implement `validate_manifest()` for required fields validation
    - Implement `validate_structure()` for directory structure checks
    - Implement `validate_dependencies()` for dependency format validation
    - Return detailed ValidationResult with errors and warnings
    - _Requirements: 1.2, 1.5, 4.1, 4.2, 4.3, 4.4_

  - [x]* 2.2 Write unit tests for Validator
    - Test valid semver formats (1.0.0, 1.2.3-alpha.1, 1.0.0+build)
    - Test invalid semver formats (1.0, v1.0.0, 1.0.0.0)
    - Test required field validation (name, version, publisher, description, license)
    - Test field format validation (name pattern, description length)
    - Test dependency constraint formats (^1.0.0, >=1.0.0,<2.0.0, ~1.2.3)
    - _Requirements: 1.2, 1.5, 4.1, 4.2, 4.3, 4.4_

  - [x]* 2.3 Write property tests for Validator
    - **Property 2: 语义化版本号验证**
    - **Validates: Requirements 1.2**
    - Generate random version strings and verify correct classification
    - **Property 5: 必填字段验证**
    - **Validates: Requirements 1.5**
    - Generate manifests with missing random required fields and verify rejection
    - **Property 13: 规范校验完整性**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
    - Generate skill packages with multiple errors and verify all are reported
    - _Requirements: 1.2, 1.5, 4.1, 4.2, 4.3, 4.4_

- [x] 3. Implement Index Builder component
  - [x] 3.1 Create `owlhub/indexer/crawler.py` for repository crawling
    - Implement GitHub API client for fetching repository contents
    - Implement SKILL.md frontmatter parsing using PyYAML
    - Handle API rate limiting and errors gracefully
    - Support authentication via GitHub token
    - _Requirements: 1.1, 4.1_

  - [x] 3.2 Create `owlhub/indexer/builder.py` for index generation
    - Implement `calculate_checksum()` using hashlib.sha256
    - Implement `crawl_repository()` to extract skill manifests
    - Implement `build_index()` to generate complete index.json
    - Support incremental updates (only process changed repos)
    - Generate index with version, generated_at, total_skills, and skills array
    - _Requirements: 1.1, 1.3, 5.3, 8.1_

  - [x]* 3.3 Write unit tests for Index Builder
    - Test building index from empty repository list (expect empty index)
    - Test building index with single skill
    - Test building index with multiple versions of same skill
    - Test handling invalid SKILL.md frontmatter
    - Test handling missing required files
    - Test checksum calculation consistency
    - _Requirements: 1.1, 1.3, 5.3, 8.1_

  - [x]* 3.4 Write property tests for Index Builder
    - **Property 1: 版本发布与检索**
    - **Validates: Requirements 1.1**
    - Generate random valid skill manifests, publish to index, verify retrieval
    - **Property 3: 版本历史不变性**
    - **Validates: Requirements 1.3**
    - Generate skill with multiple versions, verify all versions remain accessible
    - **Property 16: Checksum 完整性验证**
    - **Validates: Requirements 5.3**
    - Generate random files, calculate checksum → transfer → recalculate, verify match
    - _Requirements: 1.1, 1.3, 5.3_

- [x] 4. Implement CLI Client for skill management
  - [x] 4.1 Create `owlclaw/cli/skill.py` with CLI commands
    - Implement `search` command with query and tag filtering
    - Implement `install` command with version specification support
    - Implement `list` command to show installed skills
    - Implement `validate` command for local skill package validation
    - Use Click or Typer for CLI framework
    - Add rich output formatting for better UX
    - _Requirements: 2.1, 2.5, 3.1, 3.2, 4.5_

  - [x] 4.2 Implement skill installation logic
    - Download skill package from download_url
    - Verify checksum before extraction
    - Extract to installation directory
    - Validate extracted skill structure
    - Handle installation errors and rollback on failure
    - _Requirements: 3.1, 3.2, 3.5, 5.3_

  - [x] 4.3 Implement lock file management
    - Create `skill-lock.json` schema with version, generated_at, skills
    - Implement lock file generation after installation
    - Implement lock file reading for reproducible installs
    - Store resolved versions, URLs, and checksums
    - _Requirements: 3.4_

  - [x]* 4.4 Write unit tests for CLI Client
    - Test search with no results
    - Test install of already installed skill
    - Test install of non-existent version
    - Test update when no updates available
    - Test lock file generation and format
    - Test installation rollback on validation failure
    - _Requirements: 2.1, 3.1, 3.2, 3.4, 3.5_

  - [x]* 4.5 Write property tests for CLI Client
    - **Property 6: 多维度搜索**
    - **Validates: Requirements 2.1, 2.2**
    - Generate random skill sets and queries, verify results match and are sorted correctly
    - **Property 9: 技能安装正确性**
    - **Validates: Requirements 3.1, 3.2**
    - Generate random skill packages, install, verify file structure and checksum
    - **Property 11: Lock 文件一致性**
    - **Validates: Requirements 3.4**
    - Install random skills, generate lock, reinstall from lock, verify identical versions
    - **Property 12: 校验失败拒绝**
    - **Validates: Requirements 3.5**
    - Generate invalid skill packages, verify installation rejected and state unchanged
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.4, 3.5_

- [x] 5. Set up GitHub Actions workflow for index publishing
  - Create `.github/workflows/owlhub-build-index.yml`
  - Configure workflow to run Index Builder on schedule (hourly)
  - Configure workflow to run on manual trigger
  - Publish generated index.json to GitHub Pages
  - Add workflow for validating PRs that add new skills
  - _Requirements: 8.1, 8.2_

- [x]* 5.1 Write integration test for Phase 1 end-to-end flow
  - Test complete publish flow: create skill → validate → build index → publish
  - Test complete install flow: search → download → validate → install → lock
  - Verify index.json is accessible and parseable by CLI
  - **Property 25: 静态站点索引可访问性**
  - **Validates: Requirements 8.2**
  - _Requirements: 1.1, 2.1, 3.1, 8.1, 8.2_

- [ ] 6. Create configuration and documentation for Phase 1
  - Create `.owlhub/config.yaml` with index_url, repositories, update_interval
  - Document CLI commands and usage examples
  - Document skill package structure requirements
  - Document index.json schema
  - Add Phase 1 architecture diagram to docs
  - _Requirements: 8.1, 8.5_

- [ ] 7. Checkpoint - Phase 1 Complete
  - Ensure all Phase 1 tests pass
  - Verify CLI can search and install skills from generated index
  - Verify index.json is valid and accessible
  - Ask user if questions arise before proceeding to Phase 2

## Phase 2: Static Site Mode (Enhanced Discovery)

- [ ] 8. Implement Statistics Tracker for GitHub-based metrics
  - [ ] 8.1 Create `owlhub/statistics/tracker.py` with StatisticsTracker class
    - Implement GitHub API integration for release download counts
    - Implement `get_statistics()` to fetch skill download metrics
    - Calculate downloads_last_30d from GitHub API data
    - Cache statistics to avoid rate limiting
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ]* 8.2 Write unit tests for Statistics Tracker
    - Test fetching statistics from GitHub API
    - Test caching behavior
    - Test handling API rate limits
    - Test statistics aggregation
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ]* 8.3 Write property test for statistics accuracy
    - **Property 18: 统计计数准确性**
    - **Validates: Requirements 6.1, 6.2, 6.3**
    - Simulate N download/install operations, verify counts reflect operations accurately
    - _Requirements: 6.1, 6.2, 6.3_

- [ ] 9. Enhance Index Builder with statistics and search metadata
  - [ ] 9.1 Update IndexBuilder to include statistics in index.json
    - Integrate StatisticsTracker to fetch download counts
    - Add statistics field to each skill entry
    - Include total_downloads, downloads_last_30d, last_updated
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ] 9.2 Generate search index metadata for lunr.js
    - Create searchable text from skill name, description, tags
    - Generate search index JSON for client-side search
    - Optimize index size for fast loading
    - _Requirements: 2.1, 2.2_

  - [ ]* 9.3 Write unit tests for enhanced Index Builder
    - Test statistics integration in index generation
    - Test search metadata generation
    - Test backward compatibility with Phase 1 index format
    - _Requirements: 2.1, 6.1, 8.4_

- [ ] 10. Implement Static Site Generator
  - [ ] 10.1 Create `owlhub/site/generator.py` with SiteGenerator class
    - Set up Jinja2 templating environment
    - Implement page generation for skill list, detail, search
    - Generate RSS feed for new skills and updates
    - Generate sitemap.xml for SEO
    - _Requirements: 2.1, 2.3, 8.2_

  - [ ] 10.2 Create HTML templates with Jinja2
    - Create base.html template with navigation and footer
    - Create index.html for skill listing with sorting and filtering
    - Create skill_detail.html for individual skill pages
    - Create search.html with client-side search using lunr.js
    - Add responsive CSS for mobile compatibility
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 10.3 Create statistics dashboard page
    - Create dashboard.html template
    - Display top skills by downloads
    - Display recently updated skills
    - Display total skills count and growth trends
    - Add Chart.js for visualization
    - _Requirements: 6.1, 6.2, 6.5_

  - [ ]* 10.4 Write unit tests for Static Site Generator
    - Test HTML generation from index data
    - Test RSS feed generation
    - Test search index generation
    - Test template rendering with various data
    - _Requirements: 2.1, 2.3, 8.2_

  - [ ]* 10.5 Write property tests for site generation
    - **Property 7: 技能详情完整性**
    - **Validates: Requirements 2.3**
    - Generate random skills, verify detail pages contain all required information
    - **Property 8: 分页一致性**
    - **Validates: Requirements 2.4**
    - Generate large skill set, verify pagination produces complete non-duplicate results
    - _Requirements: 2.3, 2.4_

- [ ] 11. Implement Review System (Phase 2 - automated validation)
  - [ ] 11.1 Create `owlhub/review/system.py` with ReviewSystem class
    - Implement `submit_for_review()` to create review records
    - Implement automated validation checks using Validator
    - Generate review reports with validation results
    - Store review records in JSON files (Phase 2) or database (Phase 3)
    - _Requirements: 7.1, 7.4_

  - [ ]* 11.2 Write unit tests for Review System
    - Test review submission and record creation
    - Test automated validation integration
    - Test review status transitions
    - _Requirements: 7.1, 7.4_

  - [ ]* 11.3 Write property test for review workflow
    - **Property 20: 审核状态转换**
    - **Validates: Requirements 7.1, 7.4**
    - Submit random skills for review, execute approve/reject, verify state transitions
    - _Requirements: 7.1, 7.4_

- [ ] 12. Implement tagging and categorization
  - [ ] 12.1 Add tag-based filtering to CLI search command
    - Support multiple tag filters with AND/OR logic
    - Display tags in search results
    - _Requirements: 2.1, 7.2_

  - [ ] 12.2 Add tag browsing to static site
    - Create tag cloud on homepage
    - Create tag detail pages showing skills by tag
    - Add tag filtering to search interface
    - _Requirements: 2.1, 7.2_

  - [ ]* 12.3 Write property test for tag-based retrieval
    - **Property 21: 标签分类检索**
    - **Validates: Requirements 7.2**
    - Generate skills with random tags, verify retrieval by tag works correctly
    - _Requirements: 7.2_

- [ ] 13. Update GitHub Actions workflow for Phase 2
  - Update workflow to run StatisticsTracker before IndexBuilder
  - Update workflow to run SiteGenerator after IndexBuilder
  - Deploy generated static site to GitHub Pages
  - Configure custom domain if needed
  - _Requirements: 8.2_

- [ ] 14. Add CLI update command
  - [ ] 14.1 Implement `update` command in CLI
    - Check installed skills against index for newer versions
    - Support updating single skill or all skills
    - Update lock file after successful updates
    - Display update summary (what was updated, versions)
    - _Requirements: 3.3_

  - [ ]* 14.2 Write unit tests for update command
    - Test update detection when newer version exists
    - Test no-op when already on latest version
    - Test update of single skill vs all skills
    - Test lock file update after upgrade
    - _Requirements: 3.3_

  - [ ]* 14.3 Write property test for version update detection
    - **Property 10: 版本更新检测**
    - **Validates: Requirements 3.3**
    - Install old version, publish new version, verify update command detects it
    - _Requirements: 3.3_

- [ ] 15. Implement version state management
  - [ ] 15.1 Add version state support to IndexBuilder
    - Parse version state from SKILL.md or repository tags
    - Include state in index.json for each version
    - Support DRAFT, RELEASED, DEPRECATED states
    - _Requirements: 1.4_

  - [ ] 15.2 Update CLI to respect version states
    - Filter out DRAFT versions in search results (unless --include-draft flag)
    - Show deprecation warnings when installing DEPRECATED versions
    - Display version state in `list` command output
    - _Requirements: 1.4_

  - [ ]* 15.3 Write property test for version state management
    - **Property 4: 版本状态管理**
    - **Validates: Requirements 1.4**
    - Generate versions with random states, verify queries return correct state
    - _Requirements: 1.4_

- [ ]* 16. Write integration tests for Phase 2 end-to-end flows
  - Test complete site generation: index → statistics → site → deploy
  - Test CLI compatibility with Phase 2 index format
  - Test search functionality on generated site
  - Test statistics display on dashboard
  - **Property 26: 阶段间向后兼容性**
  - **Validates: Requirements 8.4**
  - Verify Phase 1 CLI can read Phase 2 index data
  - _Requirements: 2.1, 6.1, 8.2, 8.4_

- [ ] 17. Update documentation for Phase 2
  - Document static site features and navigation
  - Document statistics tracking and dashboard
  - Document tag-based search and filtering
  - Document review system (automated validation)
  - Add Phase 2 architecture diagram
  - _Requirements: 8.5_

- [ ] 18. Checkpoint - Phase 2 Complete
  - Ensure all Phase 2 tests pass
  - Verify static site is generated and accessible
  - Verify statistics are displayed correctly
  - Verify CLI remains compatible with new index format
  - Ask user if questions arise before proceeding to Phase 3

## Phase 3: Service API Mode (Full Service)

- [ ] 19. Set up database infrastructure
  - [ ] 19.1 Create database schema with Alembic migrations
    - Create `migrations/versions/` migration for skills table
    - Create migration for skill_versions table with foreign key
    - Create migration for skill_statistics table
    - Create migration for review_records table
    - Add indexes for common queries (name, publisher, tags)
    - _Requirements: 1.1, 1.3, 6.1, 7.1_

  - [ ] 19.2 Create SQLAlchemy models
    - Create `owlhub/models/skill.py` with Skill model
    - Create `owlhub/models/version.py` with SkillVersion model
    - Create `owlhub/models/statistics.py` with SkillStatistics model
    - Create `owlhub/models/review.py` with ReviewRecord model
    - Add relationships and cascade rules
    - _Requirements: 1.1, 1.3, 6.1, 7.1_

  - [ ]* 19.3 Write unit tests for database models
    - Test model creation and relationships
    - Test unique constraints (publisher + name)
    - Test cascade deletes
    - Test query performance with indexes
    - _Requirements: 1.1, 1.3_

- [ ] 20. Implement FastAPI service foundation
  - [ ] 20.1 Create `owlhub/api/app.py` with FastAPI application
    - Set up FastAPI app with CORS middleware
    - Configure database connection pooling
    - Add health check endpoint
    - Add OpenAPI documentation configuration
    - Set up structured logging
    - _Requirements: 8.3_

  - [ ] 20.2 Create API request/response schemas
    - Create Pydantic models for SkillSearchResponse, SkillDetail, VersionInfo
    - Create models for PublishRequest, PublishResponse, UpdateStateRequest
    - Add validation rules and examples
    - _Requirements: 2.1, 2.3_

  - [ ]* 20.3 Write unit tests for API schemas
    - Test schema validation with valid data
    - Test schema validation with invalid data
    - Test serialization/deserialization
    - _Requirements: 2.1, 2.3_

- [ ] 21. Implement Registry API endpoints
  - [ ] 21.1 Create `owlhub/api/routes/skills.py` with search endpoint
    - Implement `GET /api/v1/skills` with query, tags, sort_by, pagination
    - Support sorting by downloads, updated_at, name
    - Implement efficient database queries with joins
    - Add response caching for common queries
    - _Requirements: 2.1, 2.2, 2.4_

  - [ ] 21.2 Implement skill detail and version endpoints
    - Implement `GET /api/v1/skills/{publisher}/{name}` for skill details
    - Implement `GET /api/v1/skills/{publisher}/{name}/versions` for version list
    - Include statistics and dependency information
    - _Requirements: 2.3_

  - [ ]* 21.3 Write unit tests for read-only API endpoints
    - Test search with various query parameters
    - Test pagination edge cases (empty results, last page)
    - Test sorting by different fields
    - Test skill detail retrieval
    - Test version listing
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ]* 21.4 Write property tests for API search and pagination
    - **Property 6: 多维度搜索** (API version)
    - **Validates: Requirements 2.1, 2.2**
    - Test search results match query and are correctly sorted
    - **Property 8: 分页一致性** (API version)
    - **Validates: Requirements 2.4**
    - Test pagination produces complete non-duplicate results
    - _Requirements: 2.1, 2.2, 2.4_

- [ ] 22. Implement Authentication and Authorization
  - [ ] 22.1 Create `owlhub/api/auth.py` with OAuth2 integration
    - Implement GitHub OAuth2 flow
    - Implement JWT token generation and validation
    - Create API key management for programmatic access
    - Store user sessions securely
    - _Requirements: 5.1_

  - [ ] 22.2 Add authentication middleware to FastAPI
    - Protect write endpoints with authentication
    - Implement role-based access control (publisher, reviewer, admin)
    - Add rate limiting per user/API key
    - _Requirements: 5.1_

  - [ ]* 22.3 Write unit tests for authentication
    - Test OAuth2 flow with valid credentials
    - Test JWT token validation
    - Test API key authentication
    - Test unauthorized access rejection
    - _Requirements: 5.1_

  - [ ]* 22.4 Write property test for authentication protection
    - **Property 14: 身份验证保护**
    - **Validates: Requirements 5.1**
    - Send unauthenticated publish requests, verify 401 responses
    - _Requirements: 5.1_

- [ ] 23. Implement skill publishing endpoints
  - [ ] 23.1 Create publish and update endpoints
    - Implement `POST /api/v1/skills` for publishing new skills
    - Implement `PUT /api/v1/skills/{publisher}/{name}/versions/{version}/state` for state updates
    - Validate publisher matches authenticated user
    - Integrate with Validator for automatic validation
    - Trigger review workflow on publish
    - _Requirements: 1.1, 1.4, 5.1, 7.1_

  - [ ] 23.2 Implement audit logging for publish operations
    - Create `owlhub/api/audit.py` with audit logging
    - Log publisher identity, timestamp, changes for all publish operations
    - Store audit logs in database or separate audit log file
    - Provide audit log query API for admins
    - _Requirements: 5.2_

  - [ ]* 23.3 Write unit tests for publish endpoints
    - Test successful skill publication
    - Test version state updates
    - Test publisher validation (can only publish own skills)
    - Test validation integration
    - Test audit log creation
    - _Requirements: 1.1, 1.4, 5.1, 5.2, 7.1_

  - [ ]* 23.4 Write property tests for publishing
    - **Property 1: 版本发布与检索** (API version)
    - **Validates: Requirements 1.1**
    - Publish random skills via API, verify retrieval
    - **Property 15: 发布审计日志**
    - **Validates: Requirements 5.2**
    - Execute publish operations, verify audit logs contain complete information
    - _Requirements: 1.1, 5.2_

- [ ] 24. Implement real-time Statistics Service
  - [ ] 24.1 Update StatisticsTracker for database-backed tracking
    - Implement `record_download()` to write to skill_statistics table
    - Implement `record_install()` with user_id tracking
    - Implement aggregation queries for total and time-windowed stats
    - Add background job for daily statistics aggregation
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ] 24.2 Create statistics API endpoints
    - Implement `GET /api/v1/skills/{publisher}/{name}/statistics`
    - Implement `GET /api/v1/statistics/export` with format parameter
    - Support JSON and CSV export formats
    - Add admin-only endpoint for full statistics dump
    - _Requirements: 6.3, 6.4, 6.5_

  - [ ]* 24.3 Write unit tests for Statistics Service
    - Test download/install event recording
    - Test statistics aggregation
    - Test concurrent event handling
    - Test export format generation
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ]* 24.4 Write property tests for statistics
    - **Property 18: 统计计数准确性** (database version)
    - **Validates: Requirements 6.1, 6.2, 6.3**
    - Execute N operations, verify counts are accurate
    - **Property 19: 统计数据导出完整性**
    - **Validates: Requirements 6.4**
    - Export statistics, verify completeness and schema compliance
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 25. Implement full Review System with human workflow
  - [ ] 25.1 Enhance ReviewSystem for Phase 3
    - Update to use database for review records
    - Implement `approve()` and `reject()` methods
    - Implement `appeal()` for rejected skills
    - Add reviewer assignment logic
    - Send notifications on review status changes
    - _Requirements: 7.1, 7.4, 7.5_

  - [ ] 25.2 Create review API endpoints
    - Implement `GET /api/v1/reviews/pending` for reviewers
    - Implement `POST /api/v1/reviews/{id}/approve` for approval
    - Implement `POST /api/v1/reviews/{id}/reject` with reason
    - Implement `POST /api/v1/reviews/{id}/appeal` for publishers
    - Restrict endpoints to reviewer/admin roles
    - _Requirements: 7.1, 7.4, 7.5_

  - [ ]* 25.3 Write unit tests for Review System Phase 3
    - Test review record creation in database
    - Test approve/reject workflows
    - Test appeal submission and tracking
    - Test reviewer permissions
    - _Requirements: 7.1, 7.4, 7.5_

  - [ ]* 25.4 Write property tests for review workflow
    - **Property 20: 审核状态转换** (database version)
    - **Validates: Requirements 7.1, 7.4**
    - Test state transitions with database persistence
    - **Property 23: 申诉记录保存**
    - **Validates: Requirements 7.5**
    - Submit random appeals, verify records are saved with complete information
    - _Requirements: 7.1, 7.4, 7.5_

- [ ] 26. Implement blacklist and moderation features
  - [ ] 26.1 Create blacklist management
    - Create `owlhub/models/blacklist.py` with Blacklist model
    - Implement blacklist API endpoints (admin-only)
    - Add blacklist checking to search and install flows
    - Support blacklisting by skill name or publisher
    - _Requirements: 5.4, 7.3_

  - [ ] 26.2 Implement skill takedown functionality
    - Implement `POST /api/v1/skills/{publisher}/{name}/takedown` endpoint
    - Mark skills as taken down without deleting data
    - Hide taken down skills from public index and search
    - Allow already-installed users to continue using
    - Record takedown reason and timestamp
    - _Requirements: 7.3_

  - [ ]* 26.3 Write unit tests for blacklist and takedown
    - Test blacklist addition and removal
    - Test blacklist filtering in search
    - Test blacklist blocking in install
    - Test takedown hiding from public views
    - Test takedown preservation for existing installs
    - _Requirements: 5.4, 7.3_

  - [ ]* 26.4 Write property tests for blacklist filtering
    - **Property 17: 黑名单过滤**
    - **Validates: Requirements 5.4**
    - Add random skills to blacklist, verify they don't appear in search/install
    - **Property 22: 下架技能隐藏**
    - **Validates: Requirements 7.3**
    - Take down random skills, verify hidden from public but accessible to existing users
    - _Requirements: 5.4, 7.3_

- [ ] 27. Update CLI to support API mode
  - [ ] 27.1 Add API client to CLI
    - Create `owlclaw/cli/api_client.py` for API communication
    - Support both static index mode and API mode via configuration
    - Implement authentication token management for API mode
    - Add automatic fallback to static index if API unavailable
    - _Requirements: 8.3, 8.4_

  - [ ] 27.2 Add publish command to CLI
    - Implement `owlclaw skill publish <path>` command
    - Validate skill package locally before publishing
    - Authenticate with API and upload skill metadata
    - Display publish status and review information
    - _Requirements: 1.1, 5.1_

  - [ ]* 27.3 Write unit tests for API client
    - Test API mode vs static index mode selection
    - Test authentication token handling
    - Test fallback behavior on API failure
    - Test publish command flow
    - _Requirements: 8.3, 8.4_

  - [ ]* 27.4 Write integration test for CLI API compatibility
    - **Property 26: 阶段间向后兼容性** (complete test)
    - **Validates: Requirements 8.4**
    - Test Phase 1 CLI with Phase 2 index
    - Test Phase 1/2 CLI with Phase 3 API
    - Verify backward compatibility maintained
    - _Requirements: 8.4_

- [ ] 28. Implement dependency resolution
  - [ ] 28.1 Create dependency resolver
    - Create `owlclaw/cli/resolver.py` with dependency resolution logic
    - Implement topological sort for dependency order
    - Detect circular dependencies and report errors
    - Resolve version constraints using semantic versioning
    - _Requirements: 3.1, 4.4_

  - [ ] 28.2 Integrate resolver into install command
    - Automatically resolve and install dependencies
    - Display dependency tree before installation
    - Add `--no-deps` flag to skip dependency installation
    - Update lock file with full dependency graph
    - _Requirements: 3.1, 3.4_

  - [ ]* 28.3 Write unit tests for dependency resolver
    - Test simple dependency chain resolution
    - Test circular dependency detection
    - Test version constraint resolution
    - Test missing dependency error handling
    - _Requirements: 3.1, 4.4_

  - [ ]* 28.4 Write integration test for dependency installation
    - Test installing skill with dependencies
    - Test dependency tree display
    - Test lock file includes all dependencies
    - Verify correct installation order
    - _Requirements: 3.1, 3.4_

- [ ] 29. Implement error handling and recovery
  - [ ] 29.1 Add comprehensive error handling to all components
    - Implement network error handling with retry logic (exponential backoff)
    - Implement validation error handling with detailed messages
    - Implement integrity error handling with cleanup
    - Implement permission error handling with helpful suggestions
    - Implement dependency conflict error handling with resolution hints
    - _Requirements: 3.5_

  - [ ] 29.2 Add error recovery mechanisms
    - Implement transaction rollback for failed installations
    - Implement cache clearing for corrupted downloads
    - Implement state recovery after interrupted operations
    - Add `--force` flag to override certain errors
    - _Requirements: 3.5_

  - [ ]* 29.3 Write unit tests for error handling
    - Test network error retry logic
    - Test validation error messages
    - Test integrity error cleanup
    - Test permission error suggestions
    - Test dependency conflict reporting
    - _Requirements: 3.5_

- [ ] 30. Add caching and performance optimizations
  - [ ] 30.1 Implement caching layer
    - Cache index.json with TTL (configurable, default 1 hour)
    - Cache downloaded skill packages
    - Cache API responses for read-only endpoints
    - Add `--no-cache` flag to bypass cache
    - Add `owlclaw skill cache clear` command
    - _Requirements: NFR-2_

  - [ ] 30.2 Optimize database queries
    - Add database indexes for common query patterns
    - Implement query result caching with Redis (optional)
    - Use database connection pooling
    - Optimize N+1 query problems with eager loading
    - _Requirements: NFR-2_

  - [ ]* 30.3 Write performance tests
    - Test search response time with large dataset (P95 < 500ms)
    - Test concurrent API requests handling
    - Test cache hit/miss behavior
    - Test database query performance
    - _Requirements: NFR-2_

- [ ] 31. Implement monitoring and observability
  - [ ] 31.1 Add structured logging
    - Use Python logging with JSON formatter
    - Log all API requests with timing
    - Log all publish/install operations
    - Log errors with full context and stack traces
    - Configure log levels via environment variables
    - _Requirements: NFR-1_

  - [ ] 31.2 Add metrics and health checks
    - Implement `/health` endpoint with dependency checks
    - Implement `/metrics` endpoint with Prometheus format
    - Track API request counts, latencies, error rates
    - Track skill download/install counts
    - Track database connection pool metrics
    - _Requirements: NFR-1_

  - [ ]* 31.3 Write tests for observability
    - Test health check endpoint responses
    - Test metrics endpoint format
    - Test logging output format
    - Test error logging includes context
    - _Requirements: NFR-1_

- [ ] 32. Create deployment configuration
  - [ ] 32.1 Create Docker configuration
    - Create `Dockerfile` for API service
    - Create `docker-compose.yml` for local development
    - Include PostgreSQL, Redis (optional) in compose
    - Configure environment variables properly
    - _Requirements: 8.3_

  - [ ] 32.2 Create Kubernetes deployment manifests
    - Create deployment.yaml for API service
    - Create service.yaml for load balancing
    - Create configmap.yaml for configuration
    - Create secret.yaml template for sensitive data
    - Create ingress.yaml for external access
    - _Requirements: 8.3_

  - [ ] 32.3 Set up CI/CD pipeline for Phase 3
    - Update GitHub Actions for API service deployment
    - Add database migration step to deployment
    - Add smoke tests after deployment
    - Configure staging and production environments
    - _Requirements: 8.3_

- [ ]* 33. Write comprehensive integration tests for Phase 3
  - Test complete publish flow via API: authenticate → validate → publish → review
  - Test complete install flow via API: search → download → verify → install
  - Test statistics tracking: download → record → aggregate → query
  - Test review workflow: submit → validate → approve/reject → notify
  - Test blacklist enforcement: add to blacklist → verify hidden from search/install
  - Test dependency resolution: install skill with deps → verify all installed
  - Test authentication: login → get token → make authenticated request
  - Test API backward compatibility with Phase 1/2 clients
  - _Requirements: 1.1, 2.1, 3.1, 5.1, 5.4, 6.1, 7.1, 8.4_

- [ ] 34. Update documentation for Phase 3
  - Document API endpoints with examples (OpenAPI/Swagger)
  - Document authentication and authorization flows
  - Document deployment procedures (Docker, Kubernetes)
  - Document database schema and migrations
  - Document monitoring and troubleshooting
  - Document security best practices
  - Add Phase 3 architecture diagram
  - Create API client examples in Python
  - _Requirements: 8.5_

- [ ] 35. Checkpoint - Phase 3 Complete
  - Ensure all Phase 3 tests pass (unit, property, integration)
  - Verify API service is running and accessible
  - Verify database migrations are applied correctly
  - Verify authentication and authorization work correctly
  - Verify monitoring and logging are operational
  - Verify CLI works in both static and API modes
  - Ask user if questions arise before final review

## Final Integration and Polish

- [ ] 36. Security hardening
  - [ ] 36.1 Implement security best practices
    - Add rate limiting to all API endpoints
    - Implement CSRF protection for web forms
    - Add input sanitization for all user inputs
    - Configure secure headers (HSTS, CSP, X-Frame-Options)
    - Implement SQL injection prevention (parameterized queries)
    - Add dependency vulnerability scanning to CI
    - _Requirements: 5.1, 5.3, 5.4_

  - [ ] 36.2 Implement checksum verification throughout
    - Verify checksums on all skill downloads
    - Generate checksums for all published skills
    - Store checksums in database and index
    - Reject installations with checksum mismatches
    - _Requirements: 5.3_

  - [ ]* 36.3 Write security tests
    - Test rate limiting enforcement
    - Test SQL injection prevention
    - Test XSS prevention in web UI
    - Test checksum verification on tampered files
    - Test authentication bypass attempts
    - _Requirements: 5.1, 5.3_

- [ ] 37. User experience improvements
  - [ ] 37.1 Enhance CLI output and feedback
    - Add progress bars for downloads
    - Add colored output for success/error/warning
    - Add verbose mode with `--verbose` flag
    - Add quiet mode with `--quiet` flag
    - Improve error messages with actionable suggestions
    - _Requirements: 2.5, 3.1_

  - [ ] 37.2 Add CLI help and documentation
    - Add comprehensive help text for all commands
    - Add examples in help output
    - Create man pages for CLI commands
    - Add shell completion scripts (bash, zsh, fish)
    - _Requirements: 2.5_

  - [ ]* 37.3 Write UX tests
    - Test CLI output formatting
    - Test progress bar display
    - Test error message clarity
    - Test help text completeness
    - _Requirements: 2.5_

- [ ] 38. Testing coverage and quality assurance
  - [ ] 38.1 Achieve coverage targets
    - Run `poetry run pytest --cov=owlhub --cov=owlclaw/cli/skill` to measure coverage
    - Ensure overall coverage ≥ 75%
    - Ensure Validator, IndexBuilder, CLIClient coverage ≥ 85%
    - Ensure install/publish critical paths coverage ≥ 90%
    - Add tests for any uncovered code paths
    - _Requirements: All_

  - [ ] 38.2 Run all property-based tests with sufficient iterations
    - Verify all 26 property tests run with ≥ 100 iterations
    - Fix any failures discovered by property tests
    - Use fixed seed for reproducibility in CI
    - Document any property test limitations
    - _Requirements: All_

  - [ ] 38.3 Perform end-to-end testing
    - Test complete user journey: search → install → use → update
    - Test complete publisher journey: create → validate → publish → review
    - Test complete admin journey: review → approve/reject → moderate
    - Test error scenarios and recovery
    - Test performance under load
    - _Requirements: All_

- [ ] 39. Documentation and examples
  - [ ] 39.1 Create comprehensive user documentation
    - Write getting started guide
    - Write skill author guide (how to create and publish skills)
    - Write CLI reference documentation
    - Write API reference documentation
    - Write troubleshooting guide
    - _Requirements: 8.5_

  - [ ] 39.2 Create example skills
    - Create 2-3 example skills demonstrating best practices
    - Include examples with dependencies
    - Include examples with different tags and categories
    - Publish examples to test registry
    - _Requirements: 8.5_

  - [ ] 39.3 Create architecture documentation
    - Document Phase 1, 2, 3 architectures with diagrams
    - Document migration paths between phases
    - Document design decisions and trade-offs
    - Document data models and schemas
    - Document API contracts and versioning strategy
    - _Requirements: 8.5_

- [ ] 40. Final validation and release preparation
  - [ ] 40.1 Run full test suite
    - Run `poetry run pytest` and ensure all tests pass
    - Run `poetry run ruff check .` and fix any linting issues
    - Run `poetry run mypy owlclaw/ owlhub/` and fix type errors
    - Run property tests with high iteration count (1000+)
    - _Requirements: All_

  - [ ] 40.2 Validate all requirements are met
    - Review requirements document and verify each acceptance criterion
    - Verify all 8 requirements have corresponding tests
    - Verify all 26 correctness properties are tested
    - Verify NFR-1 (availability ≥ 99%) and NFR-2 (P95 < 500ms) are met
    - _Requirements: All_

  - [ ] 40.3 Prepare release artifacts
    - Tag release version following semantic versioning
    - Generate changelog from commit history
    - Build distribution packages with Poetry
    - Create release notes with features, fixes, and breaking changes
    - _Requirements: 8.5_

  - [ ] 40.4 Deploy to production
    - Deploy Phase 1 (GitHub index) to production
    - Monitor for errors and performance issues
    - Verify index is accessible and CLI works
    - Plan Phase 2 and Phase 3 rollout timeline
    - _Requirements: 8.1, 8.2_

## Notes

- Tasks marked with `*` are optional testing tasks that can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- Checkpoints ensure incremental validation between phases
- Phase 1 is the minimal viable product; Phases 2 and 3 add progressive enhancements
- All code should follow owlclaw project conventions: Python 3.10+, type hints, absolute imports, pytest, Poetry
- Security is critical: never commit secrets, validate all inputs, verify checksums, authenticate publishers
- Backward compatibility must be maintained across all phases

## Requirements Coverage Summary

- Requirement 1 (版本管理): Tasks 1, 2, 3, 15, 23
- Requirement 2 (搜索): Tasks 4, 9, 10, 12, 21
- Requirement 3 (安装更新): Tasks 4, 14, 27, 28
- Requirement 4 (校验): Tasks 2, 3, 4
- Requirement 5 (安全): Tasks 3, 22, 23, 36
- Requirement 6 (统计): Tasks 8, 9, 24
- Requirement 7 (审核治理): Tasks 11, 12, 25, 26
- Requirement 8 (架构演进): Tasks 5, 6, 13, 27, 32, 34, 39

## Property Test Coverage Summary

All 26 correctness properties from the design document are covered:
- Properties 1-5: Version management (Tasks 1, 2, 3, 15, 23)
- Properties 6-8: Search and pagination (Tasks 4, 10, 21)
- Properties 9-12: Installation and validation (Tasks 4, 14, 28)
- Property 13: Validation completeness (Task 2)
- Properties 14-17: Security and authentication (Tasks 22, 23, 26, 36)
- Properties 18-19: Statistics (Tasks 8, 24)
- Properties 20-23: Review and moderation (Tasks 11, 12, 25, 26)
- Properties 24-26: Index format and compatibility (Tasks 1, 5, 16, 27)
