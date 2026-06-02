-- 珠宝行业AI智能客服系统 - 数据库初始化脚本
-- MySQL 8.0

CREATE DATABASE IF NOT EXISTS jewelry_ai DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE jewelry_ai;

-- 租户表
CREATE TABLE IF NOT EXISTS tenant (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(64) NOT NULL UNIQUE,
    tenant_name VARCHAR(100) NOT NULL,
    contact VARCHAR(50),
    phone VARCHAR(20),
    status TINYINT DEFAULT 1 COMMENT '1=正常 0=禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='租户表';

-- 用户表
CREATE TABLE IF NOT EXISTS `user` (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    channel VARCHAR(32) NOT NULL DEFAULT 'wechat',
    nickname VARCHAR(100),
    phone VARCHAR(20),
    tags VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tenant_user (tenant_id, user_id, channel),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 商品表
CREATE TABLE IF NOT EXISTS product (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(64) NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    gold_type VARCHAR(50) COMMENT '黄金类型: 足金/18K/24K等',
    diamond_size VARCHAR(50) COMMENT '钻石参数',
    price_range VARCHAR(100) COMMENT '价格区间',
    inventory INT DEFAULT 0 COMMENT '库存',
    category VARCHAR(50) COMMENT '分类: 黄金/钻石/彩宝/银饰',
    status TINYINT DEFAULT 1 COMMENT '1=上架 0=下架',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant (tenant_id),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品表';

-- 问答表
CREATE TABLE IF NOT EXISTS faq (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(50),
    sort INT DEFAULT 0 COMMENT '排序权重',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant (tenant_id),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='问答表';

-- 知识库文档表
CREATE TABLE IF NOT EXISTS knowledge_document (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    file_type VARCHAR(32) COMMENT '文件类型: pdf/docx/xlsx/md',
    content LONGTEXT COMMENT '文档内容',
    category VARCHAR(50) COMMENT '分类: 黄金/钻石/彩宝/银饰',
    status TINYINT DEFAULT 1 COMMENT '1=正常 0=禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库文档表';

-- 对话日志表
CREATE TABLE IF NOT EXISTS chat_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(64) NOT NULL,
    channel VARCHAR(32) NOT NULL DEFAULT 'wechat',
    user_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    user_query TEXT,
    ai_answer TEXT,
    intent VARCHAR(50) DEFAULT 'general' COMMENT '意图分类: product_inquiry/complaint/price_negotiation/custom_order/general',
    need_manual TINYINT DEFAULT 0 COMMENT '是否转人工: 1=是 0=否',
    manual_reason VARCHAR(255) COMMENT '转人工原因',
    used_tokens INT DEFAULT 0 COMMENT '消耗token数',
    review_status VARCHAR(20) DEFAULT 'pending' COMMENT '质检状态: pending/reviewed/flagged',
    quality_score TINYINT COMMENT '质量评分: 1-5',
    reviewer_id BIGINT COMMENT '质检员ID',
    review_comment TEXT COMMENT '质检备注',
    reviewed_at DATETIME COMMENT '质检时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tenant (tenant_id),
    INDEX idx_user (tenant_id, user_id),
    INDEX idx_session (session_id),
    INDEX idx_created (created_at),
    INDEX idx_review_status (review_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话日志表';

-- Prompt配置表
CREATE TABLE IF NOT EXISTS prompt_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id VARCHAR(64) NOT NULL UNIQUE,
    system_prompt TEXT COMMENT '系统提示词',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Prompt配置表';

-- 管理员表
CREATE TABLE IF NOT EXISTS admin_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    password VARCHAR(128) NOT NULL COMMENT 'bcrypt加密',
    role VARCHAR(32) NOT NULL COMMENT '角色: super_admin/tenant_admin/operator',
    tenant_id VARCHAR(64) COMMENT '关联租户',
    status TINYINT DEFAULT 1 COMMENT '1=正常 0=禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='管理员表';

-- 默认超级管理员由应用启动时自动创建 (用户名: admin, 密码: admin123)
-- 详见 src/db/mysql.py ensure_admin_user()
