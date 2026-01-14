package com.rivet.security;

import com.rivet.domain.entity.User;
import lombok.AllArgsConstructor;
import lombok.Getter;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

import java.util.Collection;
import java.util.Collections;
import java.util.UUID;

/**
 * Spring Security UserDetails implementation.
 * Represents the currently authenticated user.
 */
@Getter
@AllArgsConstructor
public class UserPrincipal implements UserDetails {

    private UUID id;
    private String email;
    private String password;
    private Long telegramId;
    private User.SubscriptionTier subscriptionTier;
    private Collection<? extends GrantedAuthority> authorities;

    public static UserPrincipal create(User user) {
        // For now, all users have ROLE_USER authority
        // In future, implement proper role-based access control
        Collection<GrantedAuthority> authorities = Collections.singletonList(
            new SimpleGrantedAuthority("ROLE_USER")
        );

        return new UserPrincipal(
            user.getId(),
            user.getEmail(),
            user.getPasswordHash(),
            user.getTelegramId(),
            user.getSubscriptionTier(),
            authorities
        );
    }

    @Override
    public String getUsername() {
        return email != null ? email : telegramId != null ? telegramId.toString() : id.toString();
    }

    @Override
    public String getPassword() {
        return password;
    }

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return authorities;
    }

    @Override
    public boolean isAccountNonExpired() {
        return true;
    }

    @Override
    public boolean isAccountNonLocked() {
        return true;
    }

    @Override
    public boolean isCredentialsNonExpired() {
        return true;
    }

    @Override
    public boolean isEnabled() {
        return true;
    }
}
