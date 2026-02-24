# Implementation Plan: cli-scan

## 文档联动

- requirements: `.kiro/specs/cli-scan/requirements.md`
- design: `.kiro/specs/cli-scan/design.md`
- tasks: `.kiro/specs/cli-scan/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## Overview

This implementation plan breaks down the cli-scan Python AST code scanner into incremental, testable phases. The scanner will analyze Python projects to extract function signatures, type information, docstrings, dependencies, and complexity metrics. Each task builds on previous work, with property-based tests validating correctness properties throughout.

The implementation follows a bottom-up approach: core data models → parser components → analyzer components → scanner engine → CLI interface → serialization and output.

## Tasks

- [x] 1. Set up project structure and core data models
  - Create `owlclaw/cli/scan/` package structure
  - Define core data models (FunctionSignature, Parameter, ParsedDocstring, ComplexityScore, ScanResult, etc.)
  - Define enums (ParameterKind, DocstringStyle, ComplexityLevel, ImportType, Confidence, TypeSource)
  - Set up logging configuration
  - _Requirements: 1.1, 2.1, 3.1, 6.1, 9.5, 11.2_

- [x]* 1.1 Write property test for data model serialization
  - **Property 17: JSON Serialization Round-Trip**
  - **Validates: Requirements 9.1, 14.4**

- [x]* 1.2 Write property test for YAML serialization
  - **Property 18: YAML Serialization Round-Trip**
  - **Validates: Requirements 9.2, 14.4**

- [x] 2. Implement AST parser and signature extraction
  - [x] 2.1 Implement ASTParser class
    - Write `parse_file()` method using `ast.parse()`
    - Write `extract_functions()` to find module-level functions
    - Write `extract_classes()` to find class definitions
    - Write `extract_methods()` to find class methods
    - Handle SyntaxError with detailed error reporting
    - _Requirements: 1.2, 1.3, 1.5, 13.1_
  
  - [x]* 2.2 Write property test for valid Python parsing
    - **Property 2: Valid Python Parsing**
    - **Validates: Requirements 1.2, 1.3, 13.1**
  
  - [x]* 2.3 Write property test for syntax error resilience
    - **Property 3: Syntax Error Resilience**
    - **Validates: Requirements 1.5, 11.6**
  
  - [x] 2.4 Implement SignatureExtractor class
    - Extract function name, module, qualname
    - Parse parameters from `func_node.args`
    - Extract type annotations using `ast.unparse()`
    - Identify parameter kinds (positional, keyword, *args, **kwargs)
    - Extract decorators
    - Detect async functions and generators
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [x]* 2.5 Write property test for complete signature extraction
    - **Property 4: Complete Signature Extraction**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
  
  - [x]* 2.6 Write property test for signature round-trip consistency
    - **Property 5: Signature Round-Trip Consistency**
    - **Validates: Requirements 13.4**
  
  - [x]* 2.7 Write unit tests for signature extraction edge cases
    - Test function with no parameters
    - Test function with *args and **kwargs
    - Test function with complex type hints (Union, Optional, Generic)
    - Test async function
    - Test generator function with yield
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3. Checkpoint - Ensure parser tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement docstring parser
  - [x] 4.1 Implement DocstringParser class
    - Write `detect_style()` to identify Google/NumPy/reStructuredText styles
    - Parse Google-style docstrings (Args:, Returns:, Raises:)
    - Parse NumPy-style docstrings (Parameters, Returns, Raises with underlines)
    - Parse reStructuredText-style docstrings (:param, :returns:, :raises:)
    - Extract summary, description, parameters, returns, raises, examples
    - Preserve original formatting and indentation
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [x]* 4.2 Write property test for docstring preservation
    - **Property 6: Docstring Extraction Preservation**
    - **Validates: Requirements 3.1, 3.5**
  
  - [x]* 4.3 Write property test for structured docstring parsing
    - **Property 7: Structured Docstring Parsing**
    - **Validates: Requirements 3.3, 3.4**
  
  - [x]* 4.4 Write unit tests for docstring parsing
    - Test Google-style docstring
    - Test NumPy-style docstring
    - Test reStructuredText-style docstring
    - Test docstring with code examples
    - Test missing docstring
    - _Requirements: 3.2, 3.3, 3.4_

- [x] 5. Implement type inference
  - [x] 5.1 Implement TypeInferencer class
    - Write `infer_parameter_type()` to infer from default values
    - Write `infer_return_type()` to infer from return statements
    - Infer from assignments in function body
    - Recognize common patterns ([], {}, None)
    - Assign confidence levels (HIGH, MEDIUM, LOW)
    - Return "unknown" for uninferrable types
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [x]* 5.2 Write property test for type inference from defaults
    - **Property 8: Type Inference from Defaults**
    - **Validates: Requirements 4.1**
  
  - [x]* 5.3 Write property test for type inference fallback
    - **Property 9: Type Inference Fallback**
    - **Validates: Requirements 4.5**

- [x] 6. Implement complexity calculator
  - [x] 6.1 Implement ComplexityCalculator class
    - Write `cyclomatic_complexity()` method (count decision points)
    - Write `cognitive_complexity()` method (account for nesting)
    - Calculate LOC and SLOC (exclude blank lines and comments)
    - Count parameters
    - Calculate maximum nesting depth
    - Assign complexity level (SIMPLE/MEDIUM/COMPLEX)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_
  
  - [x]* 6.2 Write property test for complexity metrics completeness
    - **Property 13: Complexity Metrics Completeness**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
  
  - [x]* 6.3 Write unit tests for complexity calculation
    - Test simple linear function (expected: cyclomatic=1)
    - Test function with nested if statements
    - Test function with multiple loops
    - Test complexity level assignment
    - _Requirements: 6.1, 6.2, 6.5_

- [x] 7. Checkpoint - Ensure analyzer tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement dependency analyzer
  - [x] 8.1 Implement DependencyAnalyzer class
    - Write `extract_imports()` to parse import statements
    - Write `extract_calls()` to find function calls in AST
    - Classify imports as STDLIB, THIRD_PARTY, or LOCAL using `importlib.util.find_spec()`
    - Build dependency graph with nodes and edges
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [x] 8.2 Implement CyclicDependencyDetector
    - Implement Tarjan's algorithm for strongly connected components
    - Detect and report circular dependencies
    - _Requirements: 5.5, 5.6_
  
  - [x]* 8.3 Write property test for function call detection
    - **Property 10: Function Call Detection**
    - **Validates: Requirements 5.1**
  
  - [x]* 8.4 Write property test for import classification
    - **Property 11: Import Classification**
    - **Validates: Requirements 5.3, 5.4**
  
  - [x]* 8.5 Write property test for cycle detection
    - **Property 12: Cycle Detection**
    - **Validates: Requirements 5.5**
  
  - [x]* 8.6 Write unit tests for dependency analysis
    - Test function calls within same module
    - Test imported function calls
    - Test method calls on objects
    - Test circular dependency detection with fixture
    - _Requirements: 5.1, 5.2, 5.5_

- [x] 9. Implement file discovery and filtering
  - [x] 9.1 Implement FileDiscovery class
    - Traverse project directory recursively
    - Filter files by glob patterns (include/exclude)
    - Exclude virtual environments (venv, .venv, env)
    - Exclude third-party libraries (site-packages)
    - Handle symbolic links safely
    - _Requirements: 1.1, 1.6, 10.2, 10.3_
  
  - [x]* 9.2 Write property test for file discovery with exclusions
    - **Property 1: File Discovery with Exclusions**
    - **Validates: Requirements 1.1, 1.6**
  
  - [x]* 9.3 Write property test for configuration pattern filtering
    - **Property 20: Configuration Pattern Filtering**
    - **Validates: Requirements 10.2, 10.3**

- [x] 10. Implement scanner engine core
  - [x] 10.1 Implement ProjectScanner class
    - Write `scan()` method to orchestrate scanning
    - Write `_scan_file()` to scan individual files
    - Integrate ASTParser, SignatureExtractor, DocstringParser, ComplexityCalculator, DependencyAnalyzer
    - Aggregate results into ScanResult
    - Handle file system errors gracefully
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 11.1, 11.6_
  
  - [x] 10.2 Implement ScanConfig class
    - Define configuration options (paths, patterns, features, thresholds)
    - Apply feature toggles (extract_docstrings, calculate_complexity, analyze_dependencies)
    - Apply complexity threshold filtering
    - _Requirements: 10.1, 10.4, 10.5_
  
  - [x]* 10.3 Write property test for complexity threshold filtering
    - **Property 21: Complexity Threshold Filtering**
    - **Validates: Requirements 10.4**
  
  - [x]* 10.4 Write property test for feature toggle respect
    - **Property 22: Feature Toggle Respect**
    - **Validates: Requirements 10.5**
  
  - [x]* 10.5 Write property test for error logging completeness
    - **Property 25: Error Logging Completeness**
    - **Validates: Requirements 11.1**

- [x] 11. Checkpoint - Ensure scanner core tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Implement parallel processing
  - [x] 12.1 Implement ParallelExecutor class
    - Use `multiprocessing.Pool` for parallel file scanning
    - Auto-detect CPU count with `os.cpu_count()`
    - Use `functools.partial` to pass config to workers
    - Handle exceptions in worker processes
    - Ensure deterministic output ordering
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.6_
  
  - [x]* 12.2 Write property test for parallel scan determinism
    - **Property 15: Parallel Scan Determinism**
    - **Validates: Requirements 8.4**
  
  - [x]* 12.3 Write property test for parallel error handling
    - **Property 16: Parallel Error Handling**
    - **Validates: Requirements 8.6**

- [x] 13. Implement incremental scanning
  - [x] 13.1 Implement IncrementalScanner class
    - Write `get_changed_files()` using git diff
    - Write `load_cache()` to load previous scan results
    - Write `save_cache()` to persist scan results
    - Write `merge_results()` to combine cached and incremental results
    - Handle file additions, modifications, and deletions
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_
  
  - [x] 13.2 Implement ScanCache class
    - Store cache in `.owlclaw-scan-cache.json`
    - Include file paths, modification times, and scan results
    - Handle cache invalidation
    - _Requirements: 7.2, 7.3, 7.6_
  
  - [x]* 13.3 Write property test for incremental scan correctness
    - **Property 14: Incremental Scan Correctness**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**
  
  - [x]* 13.4 Write unit tests for incremental scanning
    - Test scan → modify → incremental scan
    - Test scan → delete file → incremental scan
    - Test scan → add file → incremental scan
    - _Requirements: 7.1, 7.4, 7.5_

- [x] 14. Implement configuration management
  - [x] 14.1 Implement configuration file parser
    - Parse `.owlclaw-scan.yaml` using PyYAML
    - Define configuration schema
    - Validate configuration fields (types, ranges)
    - Apply default values for missing fields
    - _Requirements: 10.1, 10.2, 10.3, 10.5, 10.6, 15.1, 15.2, 15.3_
  
  - [x]* 14.2 Write property test for configuration round-trip
    - **Property 23: Configuration Round-Trip**
    - **Validates: Requirements 15.4**
  
  - [x]* 14.3 Write property test for configuration validation
    - **Property 24: Configuration Validation**
    - **Validates: Requirements 15.2, 15.3**
  
  - [x]* 14.4 Write unit tests for configuration
    - Test loading valid configuration file
    - Test rejecting invalid field types
    - Test applying default values
    - Test glob pattern validation
    - _Requirements: 10.1, 10.6, 15.1, 15.2_

- [x] 15. Checkpoint - Ensure configuration and incremental tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 16. Implement serialization and output
  - [x] 16.1 Implement ResultSerializer base class
    - Define serialization interface
    - Handle datetime serialization
    - Handle special characters and Unicode
    - _Requirements: 9.1, 9.2, 14.1, 14.3_
  
  - [x] 16.2 Implement JSONSerializer
    - Serialize ScanResult to JSON
    - Implement custom encoder for data models
    - Support pretty printing
    - _Requirements: 9.1, 9.4, 14.1, 14.2_
  
  - [x] 16.3 Implement YAMLSerializer
    - Serialize ScanResult to YAML
    - Handle YAML-specific formatting
    - _Requirements: 9.2, 14.1_
  
  - [x] 16.4 Implement SchemaValidator
    - Define JSON schema for ScanResult
    - Validate output against schema
    - _Requirements: 9.6, 14.5_
  
  - [x]* 16.5 Write property test for output schema compliance
    - **Property 19: Output Schema Compliance**
    - **Validates: Requirements 9.6, 14.5**

- [x] 17. Implement CLI interface
  - [x] 17.1 Implement CLIApplication main entry point
    - Set up argument parser using argparse
    - Define `scan` subcommand
    - Define `config validate` subcommand
    - Handle --help and --version flags
    - _Requirements: 12.1, 12.7, 12.8_
  
  - [x] 17.2 Implement ScanCommand handler
    - Parse CLI arguments (path, format, output, incremental, workers, config, verbose)
    - Load configuration file if specified
    - Instantiate ProjectScanner with config
    - Execute scan and handle results
    - Write output to file or stdout
    - Display progress information with --verbose
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 11.4_
  
  - [x] 17.3 Implement ConfigCommand handler
    - Validate configuration file
    - Report validation errors with descriptive messages
    - _Requirements: 10.7_
  
  - [x] 17.4 Implement OutputFormatter
    - Format output for terminal display
    - Format JSON output with pretty printing
    - Format YAML output
    - Handle stdout vs file output
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  
  - [x] 17.5 Implement logging and statistics display
    - Configure Python logging module
    - Support log level configuration (DEBUG/INFO/WARNING/ERROR)
    - Display scan statistics (files scanned, failed, duration)
    - Display verbose progress information
    - _Requirements: 11.2, 11.3, 11.4, 11.5_

- [x] 18. Implement error handling and recovery
  - [x] 18.1 Add comprehensive error handling
    - Handle file system errors (FileNotFoundError, PermissionError)
    - Handle parsing errors (SyntaxError with line numbers)
    - Handle analysis errors (graceful degradation)
    - Handle serialization errors (fallback encoders)
    - Handle configuration errors (fail fast)
    - _Requirements: 1.5, 11.1, 11.6, 13.2, 14.2, 15.2_
  
  - [x]* 18.2 Write property test for scan statistics accuracy
    - **Property 26: Scan Statistics Accuracy**
    - **Validates: Requirements 9.5, 11.5**

- [x] 19. Integration and end-to-end testing
  - [x]* 19.1 Write integration test for full project scan
    - Test complete scan with all features enabled
    - Verify all components work together
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 3.1, 4.1, 5.1, 6.1_
  
  - [x]* 19.2 Write integration test for incremental scan workflow
    - Test scan → modify → incremental rescan
    - Verify cache management
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  
  - [x]* 19.3 Write integration test for CLI invocation
    - Test various CLI argument combinations
    - Test configuration file loading
    - Test output file generation (JSON and YAML)
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_
  
  - [x]* 19.4 Write integration test for error scenarios
    - Test handling of syntax errors in files
    - Test handling of missing files
    - Test handling of invalid configuration
    - _Requirements: 1.5, 11.1, 11.6, 15.2_

- [x] 20. Final checkpoint and documentation
  - Ensure all tests pass (unit, property, integration)
  - Verify test coverage meets project standards (>= 75%)
  - Run linting with `poetry run ruff check .`
  - Run type checking with `poetry run mypy owlclaw/`
  - Ask the user if questions arise or if ready for deployment

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property-based tests use `hypothesis` library with minimum 100 iterations
- All property tests must include feature and property number in comments
- Checkpoints ensure incremental validation at logical breakpoints
- Implementation follows owlclaw project conventions (Poetry, pytest, type hints, absolute imports)
- Core implementation tasks (non-test tasks) must be completed in order
- Testing tasks validate correctness properties and can catch errors earlyrty test for docstring preservation
 comments
- Checkpoints ensure incremental validation at logical breakpoints
- Implementation follows owlclaw project conventions (Poetry, pytest, type hints, absolute imports)
- Core implementation tasks (non-test tasks) must be completed in order
- Testing tasks validate correctness properties and can catch errors early
ify test coverage meets project standards (>= 75%)
  - Run linting with `poetry run ruff check .`
  - Run type checking with `poetry run mypy owlclaw/`
  - Ask the user if questions arise or if ready for deployment

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property-based tests use `hypothesis` library with minimum 100 iterations
- All property tests must include feature and property number inous CLI argument combinations
    - Test configuration file loading
    - Test output file generation (JSON and YAML)
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_
  
  - [ ]* 19.4 Write integration test for error scenarios
    - Test handling of syntax errors in files
    - Test handling of missing files
    - Test handling of invalid configuration
    - _Requirements: 1.5, 11.1, 11.6, 15.2_

- [ ] 20. Final checkpoint and documentation
  - Ensure all tests pass (unit, property, integration)
  - Ver [ ] 19. Integration and end-to-end testing
  - [ ]* 19.1 Write integration test for full project scan
    - Test complete scan with all features enabled
    - Verify all components work together
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 3.1, 4.1, 5.1, 6.1_
  
  - [ ]* 19.2 Write integration test for incremental scan workflow
    - Test scan → modify → incremental rescan
    - Verify cache management
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  
  - [ ]* 19.3 Write integration test for CLI invocation
    - Test varive error handling
    - Handle file system errors (FileNotFoundError, PermissionError)
    - Handle parsing errors (SyntaxError with line numbers)
    - Handle analysis errors (graceful degradation)
    - Handle serialization errors (fallback encoders)
    - Handle configuration errors (fail fast)
    - _Requirements: 1.5, 11.1, 11.6, 13.2, 14.2, 15.2_
  
  - [ ]* 18.2 Write property test for scan statistics accuracy
    - **Property 26: Scan Statistics Accuracy**
    - **Validates: Requirements 9.5, 11.5**

- with pretty printing
    - Format YAML output
    - Handle stdout vs file output
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  
  - [ ] 17.5 Implement logging and statistics display
    - Configure Python logging module
    - Support log level configuration (DEBUG/INFO/WARNING/ERROR)
    - Display scan statistics (files scanned, failed, duration)
    - Display verbose progress information
    - _Requirements: 11.2, 11.3, 11.4, 11.5_

- [ ] 18. Implement error handling and recovery
  - [ ] 18.1 Add comprehensi specified
    - Instantiate ProjectScanner with config
    - Execute scan and handle results
    - Write output to file or stdout
    - Display progress information with --verbose
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 11.4_
  
  - [ ] 17.3 Implement ConfigCommand handler
    - Validate configuration file
    - Report validation errors with descriptive messages
    - _Requirements: 10.7_
  
  - [ ] 17.4 Implement OutputFormatter
    - Format output for terminal display
    - Format JSON outputhema Compliance**
    - **Validates: Requirements 9.6, 14.5**

- [ ] 17. Implement CLI interface
  - [ ] 17.1 Implement CLIApplication main entry point
    - Set up argument parser using argparse
    - Define `scan` subcommand
    - Define `config validate` subcommand
    - Handle --help and --version flags
    - _Requirements: 12.1, 12.7, 12.8_
  
  - [ ] 17.2 Implement ScanCommand handler
    - Parse CLI arguments (path, format, output, incremental, workers, config, verbose)
    - Load configuration file if
    - Implement custom encoder for data models
    - Support pretty printing
    - _Requirements: 9.1, 9.4, 14.1, 14.2_
  
  - [ ] 16.3 Implement YAMLSerializer
    - Serialize ScanResult to YAML
    - Handle YAML-specific formatting
    - _Requirements: 9.2, 14.1_
  
  - [ ] 16.4 Implement SchemaValidator
    - Define JSON schema for ScanResult
    - Validate output against schema
    - _Requirements: 9.6, 14.5_
  
  - [ ]* 16.5 Write property test for output schema compliance
    - **Property 19: Output Scvalidation
    - _Requirements: 10.1, 10.6, 15.1, 15.2_

- [ ] 15. Checkpoint - Ensure configuration and incremental tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 16. Implement serialization and output
  - [ ] 16.1 Implement ResultSerializer base class
    - Define serialization interface
    - Handle datetime serialization
    - Handle special characters and Unicode
    - _Requirements: 9.1, 9.2, 14.1, 14.3_
  
  - [ ] 16.2 Implement JSONSerializer
    - Serialize ScanResult to JSON15.2, 15.3_
  
  - [ ]* 14.2 Write property test for configuration round-trip
    - **Property 23: Configuration Round-Trip**
    - **Validates: Requirements 15.4**
  
  - [ ]* 14.3 Write property test for configuration validation
    - **Property 24: Configuration Validation**
    - **Validates: Requirements 15.2, 15.3**
  
  - [ ]* 14.4 Write unit tests for configuration
    - Test loading valid configuration file
    - Test rejecting invalid field types
    - Test applying default values
    - Test glob pattern ental scanning
    - Test scan → modify → incremental scan
    - Test scan → delete file → incremental scan
    - Test scan → add file → incremental scan
    - _Requirements: 7.1, 7.4, 7.5_

- [ ] 14. Implement configuration management
  - [ ] 14.1 Implement configuration file parser
    - Parse `.owlclaw-scan.yaml` using PyYAML
    - Define configuration schema
    - Validate configuration fields (types, ranges)
    - Apply default values for missing fields
    - _Requirements: 10.1, 10.2, 10.3, 10.5, 10.6, 15.1, tions, and deletions
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_
  
  - [ ] 13.2 Implement ScanCache class
    - Store cache in `.owlclaw-scan-cache.json`
    - Include file paths, modification times, and scan results
    - Handle cache invalidation
    - _Requirements: 7.2, 7.3, 7.6_
  
  - [ ]* 13.3 Write property test for incremental scan correctness
    - **Property 14: Incremental Scan Correctness**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**
  
  - [ ]* 13.4 Write unit tests for incremnts 8.4**
  
  - [ ]* 12.3 Write property test for parallel error handling
    - **Property 16: Parallel Error Handling**
    - **Validates: Requirements 8.6**

- [ ] 13. Implement incremental scanning
  - [ ] 13.1 Implement IncrementalScanner class
    - Write `get_changed_files()` using git diff
    - Write `load_cache()` to load previous scan results
    - Write `save_cache()` to persist scan results
    - Write `merge_results()` to combine cached and incremental results
    - Handle file additions, modificaent parallel processing
  - [ ] 12.1 Implement ParallelExecutor class
    - Use `multiprocessing.Pool` for parallel file scanning
    - Auto-detect CPU count with `os.cpu_count()`
    - Use `functools.partial` to pass config to workers
    - Handle exceptions in worker processes
    - Ensure deterministic output ordering
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.6_
  
  - [ ]* 12.2 Write property test for parallel scan determinism
    - **Property 15: Parallel Scan Determinism**
    - **Validates: Requiremeerty 21: Complexity Threshold Filtering**
    - **Validates: Requirements 10.4**
  
  - [ ]* 10.4 Write property test for feature toggle respect
    - **Property 22: Feature Toggle Respect**
    - **Validates: Requirements 10.5**
  
  - [ ]* 10.5 Write property test for error logging completeness
    - **Property 25: Error Logging Completeness**
    - **Validates: Requirements 11.1**

- [ ] 11. Checkpoint - Ensure scanner core tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Implem
    - Aggregate results into ScanResult
    - Handle file system errors gracefully
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 11.1, 11.6_
  
  - [ ] 10.2 Implement ScanConfig class
    - Define configuration options (paths, patterns, features, thresholds)
    - Apply feature toggles (extract_docstrings, calculate_complexity, analyze_dependencies)
    - Apply complexity threshold filtering
    - _Requirements: 10.1, 10.4, 10.5_
  
  - [ ]* 10.3 Write property test for complexity threshold filtering
    - **Propsions**
    - **Validates: Requirements 1.1, 1.6**
  
  - [ ]* 9.3 Write property test for configuration pattern filtering
    - **Property 20: Configuration Pattern Filtering**
    - **Validates: Requirements 10.2, 10.3**

- [ ] 10. Implement scanner engine core
  - [ ] 10.1 Implement ProjectScanner class
    - Write `scan()` method to orchestrate scanning
    - Write `_scan_file()` to scan individual files
    - Integrate ASTParser, SignatureExtractor, DocstringParser, ComplexityCalculator, DependencyAnalyzerquirements: 5.1, 5.2, 5.5_

- [ ] 9. Implement file discovery and filtering
  - [ ] 9.1 Implement FileDiscovery class
    - Traverse project directory recursively
    - Filter files by glob patterns (include/exclude)
    - Exclude virtual environments (venv, .venv, env)
    - Exclude third-party libraries (site-packages)
    - Handle symbolic links safely
    - _Requirements: 1.1, 1.6, 10.2, 10.3_
  
  - [ ]* 9.2 Write property test for file discovery with exclusions
    - **Property 1: File Discovery with Exclu  - [ ]* 8.4 Write property test for import classification
    - **Property 11: Import Classification**
    - **Validates: Requirements 5.3, 5.4**
  
  - [ ]* 8.5 Write property test for cycle detection
    - **Property 12: Cycle Detection**
    - **Validates: Requirements 5.5**
  
  - [ ]* 8.6 Write unit tests for dependency analysis
    - Test function calls within same module
    - Test imported function calls
    - Test method calls on objects
    - Test circular dependency detection with fixture
    - _Rey imports as STDLIB, THIRD_PARTY, or LOCAL using `importlib.util.find_spec()`
    - Build dependency graph with nodes and edges
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [ ] 8.2 Implement CyclicDependencyDetector
    - Implement Tarjan's algorithm for strongly connected components
    - Detect and report circular dependencies
    - _Requirements: 5.5, 5.6_
  
  - [ ]* 8.3 Write property test for function call detection
    - **Property 10: Function Call Detection**
    - **Validates: Requirements 5.1**
  
n (expected: cyclomatic=1)
    - Test function with nested if statements
    - Test function with multiple loops
    - Test complexity level assignment
    - _Requirements: 6.1, 6.2, 6.5_

- [ ] 7. Checkpoint - Ensure analyzer tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement dependency analyzer
  - [ ] 8.1 Implement DependencyAnalyzer class
    - Write `extract_imports()` to parse import statements
    - Write `extract_calls()` to find function calls in AST
    - Classif
    - Calculate LOC and SLOC (exclude blank lines and comments)
    - Count parameters
    - Calculate maximum nesting depth
    - Assign complexity level (SIMPLE/MEDIUM/COMPLEX)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_
  
  - [ ]* 6.2 Write property test for complexity metrics completeness
    - **Property 13: Complexity Metrics Completeness**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
  
  - [ ]* 6.3 Write unit tests for complexity calculation
    - Test simple linear functioWrite property test for type inference from defaults
    - **Property 8: Type Inference from Defaults**
    - **Validates: Requirements 4.1**
  
  - [ ]* 5.3 Write property test for type inference fallback
    - **Property 9: Type Inference Fallback**
    - **Validates: Requirements 4.5**

- [ ] 6. Implement complexity calculator
  - [ ] 6.1 Implement ComplexityCalculator class
    - Write `cyclomatic_complexity()` method (count decision points)
    - Write `cognitive_complexity()` method (account for nesting)sing docstring
    - _Requirements: 3.2, 3.3, 3.4_

- [ ] 5. Implement type inference
  - [ ] 5.1 Implement TypeInferencer class
    - Write `infer_parameter_type()` to infer from default values
    - Write `infer_return_type()` to infer from return statements
    - Infer from assignments in function body
    - Recognize common patterns ([], {}, None)
    - Assign confidence levels (HIGH, MEDIUM, LOW)
    - Return "unknown" for uninferrable types
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [ ]* 5.2     - **Property 6: Docstring Extraction Preservation**
    - **Validates: Requirements 3.1, 3.5**
  
  - [ ]* 4.3 Write property test for structured docstring parsing
    - **Property 7: Structured Docstring Parsing**
    - **Validates: Requirements 3.3, 3.4**
  
  - [ ]* 4.4 Write unit tests for docstring parsing
    - Test Google-style docstring
    - Test NumPy-style docstring
    - Test reStructuredText-style docstring
    - Test docstring with code examples
    - Test mis
