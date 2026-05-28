import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { AppShellComponent } from './app-shell.component';

@Component({ standalone: true, template: '<p class="stub-page">stub</p>' })
class StubPage {}

describe('AppShellComponent', () => {
  let fixture: ComponentFixture<AppShellComponent>;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppShellComponent],
      providers: [
        provideRouter([
          { path: 'executions', component: StubPage },
          { path: '', redirectTo: 'executions', pathMatch: 'full' },
        ]),
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(AppShellComponent);
    router = TestBed.inject(Router);
  });

  it('renders router-outlet in main workspace', async () => {
    fixture.detectChanges();
    await router.navigateByUrl('/executions');
    fixture.detectChanges();
    const outlet = fixture.nativeElement.querySelector('router-outlet');
    expect(outlet).withContext('router-outlet').toBeTruthy();
    expect(fixture.nativeElement.querySelector('.stub-page')?.textContent).toContain('stub');
  });

  it('renders sidebar nav icons (not letter markers)', () => {
    fixture.detectChanges();
    const icons = fixture.nativeElement.querySelectorAll('.oc-nav-icon');
    expect(icons.length).toBeGreaterThan(10);
    expect(fixture.nativeElement.textContent).not.toContain('>E<');
  });
});
