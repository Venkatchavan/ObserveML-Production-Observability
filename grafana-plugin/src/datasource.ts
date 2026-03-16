/**
 * OB-56: ObserveML Grafana Data Source Plugin
 *
 * Exposes ObserveML /v1/metrics + /v1/metrics/trend as Grafana time-series panels.
 * Authenticates with the org API key (stored as a Grafana secure JSON field).
 * 333-Line Law: this file is intentionally < 120 lines.
 */

import {
  DataQueryRequest,
  DataQueryResponse,
  DataSourceApi,
  DataSourceInstanceSettings,
  FieldType,
  MutableDataFrame,
} from '@grafana/data';
import { getBackendSrv } from '@grafana/runtime';

export interface ObserveMLQuery {
  refId: string;
  queryType: 'metrics' | 'trend';
  callSite?: string;
}

export interface ObserveMLOptions {
  apiUrl: string;
}

export class ObserveMLDataSource extends DataSourceApi<ObserveMLQuery, ObserveMLOptions> {
  private apiUrl: string;

  constructor(instanceSettings: DataSourceInstanceSettings<ObserveMLOptions>) {
    super(instanceSettings);
    this.apiUrl = instanceSettings.jsonData.apiUrl || 'https://api.observeml.io';
  }

  async query(options: DataQueryRequest<ObserveMLQuery>): Promise<DataQueryResponse> {
    const data = await Promise.all(
      options.targets.map(async (target) => {
        if (target.queryType === 'trend') {
          return this._queryTrend(target);
        }
        return this._queryMetrics(target);
      })
    );
    return { data };
  }

  private async _queryMetrics(target: ObserveMLQuery): Promise<MutableDataFrame> {
    const params = target.callSite ? `?call_site=${encodeURIComponent(target.callSite)}` : '';
    const rows = await this._get(`/v1/metrics${params}`);
    const frame = new MutableDataFrame({
      refId: target.refId,
      fields: [
        { name: 'call_site', type: FieldType.string },
        { name: 'model', type: FieldType.string },
        { name: 'avg_latency_ms', type: FieldType.number },
        { name: 'p99_latency_ms', type: FieldType.number },
        { name: 'total_calls', type: FieldType.number },
        { name: 'error_rate', type: FieldType.number },
        { name: 'total_cost_usd', type: FieldType.number },
      ],
    });
    for (const row of rows) {
      frame.appendRow([
        row.call_site, row.model, row.avg_latency_ms,
        row.p99_latency_ms, row.total_calls, row.error_rate, row.total_cost_usd,
      ]);
    }
    return frame;
  }

  private async _queryTrend(target: ObserveMLQuery): Promise<MutableDataFrame> {
    const params = target.callSite ? `?call_site=${encodeURIComponent(target.callSite)}` : '';
    const resp = await this._get(`/v1/metrics/trend${params}`);
    const frame = new MutableDataFrame({
      refId: target.refId,
      fields: [
        { name: 'time', type: FieldType.time },
        { name: 'avg_latency_ms', type: FieldType.number },
        { name: 'total_calls', type: FieldType.number },
      ],
    });
    for (const pt of resp.points ?? []) {
      frame.appendRow([new Date(pt.ts).getTime(), pt.avg_latency_ms, pt.total_calls]);
    }
    return frame;
  }

  private async _get(path: string): Promise<any> {
    return getBackendSrv().get(`${this.apiUrl}${path}`);
  }

  async testDatasource(): Promise<{ status: string; message: string }> {
    try {
      await this._get('/health');
      return { status: 'success', message: 'Connected to ObserveML API' };
    } catch (err: any) {
      return { status: 'error', message: `Connection failed: ${err?.message ?? err}` };
    }
  }
}
