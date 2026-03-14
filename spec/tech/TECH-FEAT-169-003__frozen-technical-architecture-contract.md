---
id: TECH-FEAT-169-003
ssot_type: tech
title: Frozen Technical Architecture Contract
status: deprecated
version: v1
parent_id: FEAT-169
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
  superseded_by: TECH-FEAT-169-004
---

$schema: http://json-schema.org/draft-07/schema#
$id: contracts/frozen-technical-architecture-contract/v1/schema.json
title: Frozen Technical Architecture Contract
description: Schema for FEAT-169 frozen technical architecture specification
type: object
required:
- id
- ssot_type
- title
- status
- version
- parent_id
- modules
- dependencies
- risks
properties:
  id:
    type: string
    description: Unique identifier for the frozen architecture document
    pattern: ^FTA-[A-Z]+-[0-9]+-[0-9]{8}$
  ssot_type:
    type: string
    const: frozen_technical_architecture
    description: SSOT type identifier
  title:
    type: string
    description: Human-readable title
  status:
    type: string
    enum:
    - draft
    - review
    - frozen
    - deprecated
    description: Current status of the architecture
  version:
    type: string
    pattern: ^v[0-9]+$
    description: Version number
  parent_id:
    type: string
    description: Reference to parent feature (e.g., FEAT-169)
  frozen_at:
    type: string
    format: date-time
    description: ISO 8601 timestamp when architecture was frozen
  modules:
    type: array
    description: Technical modules and their implementation schemes
    items:
      type: object
      required:
      - name
      - path
      - purpose
      - components
      properties:
        name:
          type: string
        path:
          type: string
        purpose:
          type: string
        components:
          type: array
          items:
            type: object
            required:
            - name
            - type
            - responsibilities
            properties:
              name:
                type: string
              type:
                type: string
                enum:
                - class
                - function
                - enum
                - dataclass
                - interface
              responsibilities:
                type: array
                items:
                  type: string
              interfaces:
                type: array
                items:
                  type: object
                  properties:
                    method:
                      type: string
                    signature:
                      type: string
                    returns:
                      type: string
  dependencies:
    type: object
    required:
    - internal
    - external
    properties:
      internal:
        type: array
        items:
          type: object
          required:
          - module
          - path
          - purpose
          - risk_level
          properties:
            module:
              type: string
            path:
              type: string
            purpose:
              type: string
            risk_level:
              type: string
              enum:
              - low
              - medium
              - high
      external:
        type: array
        items:
          type: object
          required:
          - library
          - version
          - purpose
          - risk_level
          properties:
            library:
              type: string
            version:
              type: string
            purpose:
              type: string
            risk_level:
              type: string
              enum:
              - low
              - medium
              - high
  risks:
    type: array
    description: Technical uncertainties and mitigation strategies
    items:
      type: object
      required:
      - id
      - description
      - impact
      - probability
      - mitigation
      - fallback
      properties:
        id:
          type: string
          pattern: ^UC-[0-9]{3}$
        description:
          type: string
        impact:
          type: string
          enum:
          - low
          - medium
          - high
        probability:
          type: string
          enum:
          - low
          - medium
          - high
        mitigation:
          type: string
        fallback:
          type: string
  decisions:
    type: array
    description: Frozen architecture decisions
    items:
      type: object
      required:
      - id
      - content
      - status
      properties:
        id:
          type: string
          pattern: ^D-[0-9]{3}$
        content:
          type: string
        status:
          type: string
          const: frozen
        rationale:
          type: string
  properties:
    type: object
    properties:
      contract_key:
        type: string
      identity_kind:
        type: string
        const: ssot
