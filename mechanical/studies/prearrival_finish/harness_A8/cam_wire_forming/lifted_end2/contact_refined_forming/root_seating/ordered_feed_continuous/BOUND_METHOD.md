# Continuous ordered-feed bounds

For guide arclength s, the stored polyline p(s) has unit speed on each segment.
The orientation uses D(s) = p(s + e) - p(s - e), e = 0.002 mm, with clamped
end coordinates. Partitioning at guide knots shifted by +e and -e makes D
affine on every subinterval. Clamping breakpoints are included explicitly.

The minimum norm of an affine vector is found by projecting the origin onto
its line segment. Thus |T prime| is bounded by |D cross D prime| / min|D|^2.
For the projected-X frame, the YZ azimuth derivative is bounded by
|Dy Dz prime - Dz Dy prime| / min|(Dy,Dz)|^2. The base angular speed is at
most hypot(tangent-rate bound, azimuth-rate bound). Add the declared smooth
roll-rate bound; the helper's singular fallback is excluded by an explicit
positive projection check.

For a contact point at distance <= R from the rear datum, its speed is at
most 1 + R * angular-speed-bound. Half-interval displacement is added to
the midpoint collision clearance requirement. The active trailing-wire
prefix is taken through the interval end minus the explicit 2 mm crimp
region, so no newly fed material is omitted.

The long final stroke is exactly vertical with fixed orientation. Its box
sweep is checked directly. Own trailing material on that same axis remains
at least 2 mm behind the moving rear outside the declared crimp region;
other wires and previously completed contacts remain in the sweep checks.

The companion bound_audit.json compares all eight transformed contact
vertices at interval endpoints and interior poses against the derived
bound. This is a regression for frame/code correspondence, not the source
of the continuous proof. Numerical allowances and the assumed contact
allocation are recorded in screen.json. Real crimp shape, friction, hand
access and body-end material supply are outside this local certificate.
