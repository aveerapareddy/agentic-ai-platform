import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { routes } from '../../app.routes';
import { PolicyApiService } from '../../core/api/policy-api.service';
import { PoliciesPage } from './policies.page';

describe('PoliciesPage', () => {
  let fixture: ComponentFixture<PoliciesPage>;
  let api: jasmine.SpyObj<PolicyApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj('PolicyApiService', ['listPolicies', 'simulate']);
    api.listPolicies.and.returnValue(
      of({
        rule_pack_id: 'phase3_deterministic_v1',
        rules: [
          {
            rule_id: 'R_DEFAULT_ALLOW',
            description: 'allow',
            applies_to: ['escalate_incident'],
            decision: 'allow',
            reason: 'ok',
          },
        ],
      }),
    );
    api.simulate.and.returnValue(
      of({
        decision: 'deny',
        reason: 'denied',
        matched_rules: [{ rule_id: 'R_SCOPE_DENY' }],
        rule_references: ['R_SCOPE_DENY'],
        rule_pack_id: 'phase3_deterministic_v1',
      }),
    );
    await TestBed.configureTestingModule({
      imports: [PoliciesPage],
      providers: [{ provide: PolicyApiService, useValue: api }, provideRouter(routes)],
    }).compileComponents();
    fixture = TestBed.createComponent(PoliciesPage);
  });

  it('renders policy rules and loads catalog', () => {
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Policy rules');
    expect(el.textContent).toContain('R_DEFAULT_ALLOW');
    expect(api.listPolicies).toHaveBeenCalled();
  });

  it('runs simulation and displays decision', () => {
    fixture.detectChanges();
    fixture.componentInstance.runSimulation();
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(api.simulate).toHaveBeenCalled();
    expect(el.textContent).toContain('deny');
    expect(el.textContent).toContain('R_SCOPE_DENY');
  });

  it('shows error when catalog load fails', () => {
    api.listPolicies.and.returnValue(throwError(() => new Error('forbidden')));
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('forbidden');
  });
});
