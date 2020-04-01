# CHANGELOG
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.3.0](https://github.com/andres-fr/secv-guis/compare/v0.2.3...HEAD) - 2020-04-01

### Added

* Fixed in-between brush changing bug
* Added "objects" framework to add composite objects to the scene
* Created object to add a point list to the scene


## [0.1.0] - 2020-03-31
### Added

* Created repository with BimaskGui, which allows to load images, masks and preannotations (prototype), edit and save them.
* Added utest+codecov structure and first unit tests
* Added autodoc structure for HTML and LaTeX


### TODO:

* Objects framework logic intersects with mask update logic. At some point, the scene will probably need refactoring so that masks are also treated as objects and composite actions are part of the core design.
* Argument parser could also provide default input/output paths
* Run Qt app in other platforms or web-based
