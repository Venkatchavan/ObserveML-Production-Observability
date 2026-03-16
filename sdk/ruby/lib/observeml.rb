# frozen_string_literal: true

# ObserveML Ruby gem v0.1.0 — OB-57
#
# Observer Principle: ObserveML.track() has NO prompt or response parameter.
# Only LLM call metadata is transmitted: model, latency, tokens, cost, error.
#
# Usage:
#   require 'observeml'
#   ObserveML.configure(api_key: 'obs_live_xxxx')
#   ObserveML.track(model: 'gpt-4o', latency_ms: 320, input_tokens: 150,
#                  output_tokens: 80, cost_usd: 0.0024)
#   ObserveML.shutdown   # flush remaining events on process exit

require 'net/http'
require 'json'
require 'securerandom'
require 'uri'

module ObserveML
  VERSION      = '0.1.0'
  ENDPOINT     = '/v1/ingest'
  FLUSH_EVERY  = 5       # seconds
  BATCH_SIZE   = 50
  QUEUE_LIMIT  = 1_000

  # Accepted event keys — no prompt/response (Observer Principle).
  ALLOWED_KEYS = %i[
    model latency_ms input_tokens output_tokens cost_usd
    call_site error error_code session_id trace_id
  ].freeze

  class << self
    def configure(api_key:, base_url: 'https://api.observeml.io')
      @api_key  = api_key
      @base_url = base_url
      @queue    = SizedQueue.new(QUEUE_LIMIT)
      @mutex    = Mutex.new
      _start_flush_thread
      self
    end

    # Fire-and-forget. Drops silently when queue is full (non-blocking).
    # @param event [Hash] see ALLOWED_KEYS — no prompt/response allowed.
    def track(**event)
      raise 'Call ObserveML.configure first' unless @queue

      filtered = event.select { |k, _| ALLOWED_KEYS.include?(k) }
      filtered[:event_id] ||= SecureRandom.uuid
      @queue.push(filtered, true)  # non_block=true: drops if full
    rescue ThreadError
      # Queue full — drop silently (fire-and-forget contract)
    end

    def shutdown
      @shutdown = true
      @flush_thread&.join(10)
    end

    private

    def _start_flush_thread
      @shutdown = false
      @flush_thread = Thread.new do
        Thread.current.name = 'observeml-flush'
        loop do
          sleep FLUSH_EVERY
          _flush_batch
          break if @shutdown && @queue.empty?
        end
        _flush_batch  # final drain on shutdown
      end
      @flush_thread.abort_on_exception = false
      at_exit { shutdown }
    end

    def _flush_batch
      batch = []
      BATCH_SIZE.times { batch << @queue.pop(true) rescue break }
      return if batch.empty?

      _post(batch)
    rescue StandardError => e
      warn "[ObserveML] flush error: #{e.message}"
    end

    def _post(events)
      uri     = URI.parse(@base_url + ENDPOINT)
      http    = Net::HTTP.new(uri.host, uri.port)
      http.use_ssl = uri.scheme == 'https'
      http.open_timeout = 3
      http.read_timeout = 5

      request = Net::HTTP::Post.new(uri.path, 'Content-Type' => 'application/json',
                                              'x-api-key'     => @api_key)
      request.body = JSON.generate({ events: events })

      response = http.request(request)
      if response.code == '402'
        warn '[ObserveML] Free tier limit reached (402). Upgrade at app.observeml.io.'
      end
    rescue StandardError => e
      warn "[ObserveML] HTTP error: #{e.message}"
    end
  end
end
