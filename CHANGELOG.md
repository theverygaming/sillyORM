# Changelog

## 0.10.0

- improved documentation
- datetime fields now hae improved timezone support
- Model inheritance mechanisms have been improved
- users can now disable automatic table updates (an exception will be raised when the tables do not match)
- The abilitiy to add unique and not null constraints to fields has been added (unique and required field attributes)

**diff**: https://github.com/theverygaming/sillyORM/compare/0.9.0...0.10.0

## 0.9.0

- Fixed a bug where Model.read() would error if provide with an empty recordset
- Transform search domain field types (before field types would always be ignored for search domains)
- Runtime type checking of domains (side effect of the type transforming thing above)
- Allow searching for None/NULL values explicitly
- Recordsets can now be subscripted

**diff**: https://github.com/theverygaming/sillyORM/compare/0.8.1...0.9.0

## 0.8.1

- Fixed a bug where even if you ordered using search, Model.read would ignore the order
- Minor Documentation improvements

**diff**: https://github.com/theverygaming/sillyORM/compare/0.8.0...0.8.1

## 0.8.0

- improvements to the way type conversions are handled for read and write
- Selection field
- Significant improvements to search - added `search_count` and allowed for ordering and pagination

**diff**: https://github.com/theverygaming/sillyORM/compare/0.7.0...0.8.0

## 0.7.0

- support for extending models via _extend
- **separate database Initialisation on the Environment, you must now call env.init_tables()**
- only support naive datetime objects in the datetime field (specifying timezones resulted in unexpected behavior before)

**diff**: https://github.com/theverygaming/sillyORM/compare/0.6.0...0.7.0

## 0.6.0

- added support for setting None / NULL values on fields

**diff**: https://github.com/theverygaming/sillyORM/compare/0.5.0...0.6.0

## 0.5.0

- added a datetime field

**diff**: https://github.com/theverygaming/sillyORM/compare/0.4.0...0.5.0

## 0.4.0

- **made reading fields on recordsets with more than one record impossible**
- **search does not return None anymore, instead it returns an exmpty recorset**
- added support for len() on models

**diff**: https://github.com/theverygaming/sillyORM/compare/0.3.0...0.4.0

## 0.3.0

- added float field

**diff**: https://github.com/theverygaming/sillyORM/compare/0.2.0...0.3.0

## 0.2.0

- added Boolean field
- fixed a bug where fields would disappear if a model was inherited and documented model inheritance

**diff**: https://github.com/theverygaming/sillyORM/compare/0.1.0...0.2.0

## 0.1.0

- added Text field

**diff**: https://github.com/theverygaming/sillyORM/compare/0.0.1...0.1.0

## 0.0.1

Initial release
