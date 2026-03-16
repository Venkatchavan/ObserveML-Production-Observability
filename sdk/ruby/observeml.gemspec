# frozen_string_literal: true

Gem::Specification.new do |spec|
  spec.name          = 'observeml'
  spec.version       = '0.1.0'
  spec.authors       = ['Venkat Chavan']
  spec.email         = ['venkat@observeml.io']
  spec.summary       = 'Production observability for LLM applications'
  spec.description   = (
    'Instrument any LLM call in 3 lines. Fire-and-forget async flush. ' \
    'No prompt/response content — metadata only (Observer Principle).'
  )
  spec.homepage      = 'https://github.com/Venkatchavan/ObserveML-Production-Observability'
  spec.license       = 'MIT'
  spec.required_ruby_version = '>= 2.7'

  spec.files         = Dir['lib/**/*.rb', 'README.md', 'LICENSE']
  spec.require_paths = ['lib']

  # Zero runtime dependencies — pure stdlib (Net::HTTP, JSON, SecureRandom)
end
