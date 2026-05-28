import { JsonPipe } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { PolicyApiService } from '../../core/api/policy-api.service';
import type { PolicyListResponse, PolicySimulateResponse } from '../../core/models/policy.models';

@Component({
  selector: 'app-policies-page',
  standalone: true,
  imports: [FormsModule, RouterLink, JsonPipe],
  template: `
    <p class="back-link">
      <a routerLink="/executions">← Executions</a>
    </p>
    <h1 class="oc-page-title">Policy rules</h1>
    <p class="oc-page-lead">
      Read-only catalog and simulation via <span class="mono">GET /v1/policies</span> and
      <span class="mono">POST /v1/policies/simulate</span>. Gateway enforces access; policy-engine
      evaluates rules.
    </p>

    @if (loadError) {
      <div class="oc-error" role="alert">{{ loadError }}</div>
    }
    @if (loadingRules) {
      <p class="oc-loading">Loading rules…</p>
    } @else if (catalog) {
      <p class="oc-meta">Rule pack: <span class="mono">{{ catalog.rule_pack_id }}</span></p>
      <section class="oc-panel">
        <h2 class="oc-section-title">Registered rules</h2>
        <table class="oc-table">
          <thead>
            <tr>
              <th>Rule ID</th>
              <th>Applies to</th>
              <th>Decision</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            @for (rule of catalog.rules; track rule.rule_id) {
              <tr>
                <td class="mono">{{ rule.rule_id }}</td>
                <td>{{ rule.applies_to.join(', ') }}</td>
                <td><span [class]="decisionClass(rule.decision)">{{ rule.decision }}</span></td>
                <td>{{ rule.description }}</td>
              </tr>
            }
          </tbody>
        </table>
      </section>
    }

    <section class="oc-panel" style="margin-top: var(--space-5)">
      <h2 class="oc-section-title">Simulate decision</h2>
      <div class="oc-filters">
        <label>
          Action type
          <input type="text" [(ngModel)]="actionType" name="actionType" />
        </label>
        <label>
          Risk level
          <select [(ngModel)]="riskLevel" name="riskLevel">
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </select>
        </label>
        <label>
          Environment
          <input type="text" [(ngModel)]="environment" name="environment" />
        </label>
        <label>
          Policy scope
          <input type="text" [(ngModel)]="policyScope" name="policyScope" />
        </label>
        <button type="button" class="oc-btn" (click)="runSimulation()" [disabled]="simulating">
          Simulate
        </button>
      </div>
      @if (simulateError) {
        <div class="oc-error" role="alert">{{ simulateError }}</div>
      }
      @if (simulating) {
        <p class="oc-loading">Running simulation…</p>
      } @else if (simResult) {
        <div class="oc-stat-row">
          <div class="oc-stat-card">
            <div class="oc-stat-card__label">Decision</div>
            <div class="oc-stat-card__value">
              <span [class]="decisionClass(simResult.decision)">{{ simResult.decision }}</span>
            </div>
          </div>
          <div class="oc-stat-card">
            <div class="oc-stat-card__label">Matched rules</div>
            <div class="oc-stat-card__value">{{ simResult.rule_references.length }}</div>
          </div>
        </div>
        <p class="oc-meta"><strong>Reason:</strong> {{ simResult.reason }}</p>
        @if (simResult.rule_references.length) {
          <p class="oc-meta">
            <strong>Rule references:</strong>
            <span class="mono">{{ simResult.rule_references.join(', ') }}</span>
          </p>
        }
        @if (simResult.matched_rules.length) {
          <h3 class="oc-section-title" style="margin-top: var(--space-4)">Matched rule detail</h3>
          <pre class="oc-pre">{{ simResult.matched_rules | json }}</pre>
        }
      }
    </section>
  `,
  styles: ``,
})
export class PoliciesPage implements OnInit {
  catalog: PolicyListResponse | null = null;
  loadingRules = false;
  loadError: string | null = null;

  actionType = 'escalate_incident';
  riskLevel = 'high';
  environment = 'dev';
  policyScope = 'default';

  simulating = false;
  simulateError: string | null = null;
  simResult: PolicySimulateResponse | null = null;

  constructor(private readonly policyApi: PolicyApiService) {}

  ngOnInit(): void {
    this.loadRules();
  }

  loadRules(): void {
    this.loadingRules = true;
    this.loadError = null;
    this.policyApi.listPolicies().subscribe({
      next: (data) => {
        this.catalog = data;
        this.loadingRules = false;
      },
      error: (err: Error) => {
        this.loadError = err.message;
        this.loadingRules = false;
      },
    });
  }

  runSimulation(): void {
    this.simulating = true;
    this.simulateError = null;
    this.simResult = null;
    this.policyApi
      .simulate({
        action_type: this.actionType,
        risk_level: this.riskLevel,
        execution_context: {
          environment: this.environment,
          policy_scope: this.policyScope,
        },
      })
      .subscribe({
        next: (res) => {
          this.simResult = res;
          this.simulating = false;
        },
        error: (err: Error) => {
          this.simulateError = err.message;
          this.simulating = false;
        },
      });
  }

  decisionClass(decision: string): string {
    const d = decision.toLowerCase();
    if (d === 'allow') return 'status-badge status--completed';
    if (d === 'deny') return 'status-badge status--failed';
    if (d === 'conditional') return 'status-badge status--approval';
    return 'status-badge status--neutral';
  }
}
