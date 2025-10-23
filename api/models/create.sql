drop table tenants;
CREATE TABLE tenants (
--     id uuid PRIMARY KEY NOT NULL,
--     tenant_id varchar(255) NOT NULL,
    tenant_id varchar(50) PRIMARY KEY NOT NULL,
    tenant_name varchar(500) NOT NULL,
    brand_settings jsonb,
    ai_model_preferences jsonb,
    compliance_settings jsonb,
    feature_flags jsonb,

    allowed_origins jsonb,
    rate_limit_config jsonb,

    enable_audit_logging BOOLEAN NOT NULL DEFAULT FALSE,
    enable_rate_limiting BOOLEAN NOT NULL DEFAULT FALSE,
    enable_device_validation BOOLEAN NOT NULL DEFAULT FALSE,

    area_id varchar(50) NOT NULL,
    industry varchar(50) NOT NULL,
    company_size bigint NOT NULL,
    user_count bigint NOT NULL,
    status varchar(50) NULL,
    tenant_status varchar(50) NULL,
    creator varchar(50) NOT NULL,
    editor varchar(50) NULL,
    expires_at TIMESTAMPTZ NULL DEFAULT CURRENT_TIMESTAMP, -- 使用当前时区的时间戳作为默认值
    features jsonb,

    is_active BOOLEAN NULL DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 使用当前时区的时间戳作为默认值
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 使用当前时区的时间戳作为默认值

    last_access TIMESTAMPTZ NULL DEFAULT CURRENT_TIMESTAMP,
    total_requests bigint NOT NULL DEFAULT 0,

    constraint uk_tenant_id_is_active UNIQUE (tenant_id, is_active)
);

CREATE TYPE tenant_status AS ENUM ('ACTIVE', 'BANNED', 'CLOSED');
CREATE TYPE status AS ENUM ('ACTIVE', 'BANNED', 'CLOSED');


drop table assistant;
CREATE TABLE assistant (
    id uuid PRIMARY KEY NOT NULL,

    tenant_id varchar(255) NOT NULL,
    -- tenant_name varchar(500) NOT NULL,
    assistant_id varchar(500) NOT NULL,
    assistant_name varchar(500) NOT NULL,
    assistant_status varchar(100) NOT NULL,
    assistant_sex varchar(100) NULL, -- todo 应该是 not null
    assistant_phone varchar(100) NULL, -- todo 应该是 not null
    assistant_personality_type  varchar(100) NOT NULL, -- "助理个性类型"
    assistant_expertise_level varchar(100) NOT NULL, -- "专业等级"
    assistant_sales_style jsonb NOT NULL , -- 销售风格
    assistant_voice_tone jsonb NOT NULL , -- 语音语调配置
    assistant_specializations jsonb NOT NULL ,    -- 专业领域列表
    assistant_working_hours jsonb NOT NULL , -- 工作时间配置
    assistant_max_concurrent_customers int NOT NULL default 1, -- 最大并发客户数
    assistant_permissions jsonb NOT NULL , -- 助理权限列表
    assistant_profile jsonb NOT NULL , -- 助理个人资料信息

    is_active BOOLEAN NULL DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 使用当前时区的时间戳作为默认值
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 使用当前时区的时间戳作为默认值
    last_active_at TIMESTAMPTZ NULL DEFAULT CURRENT_TIMESTAMP, -- 使用当前时区的时间戳作为默认值
    registered_devices jsonb,

    constraint uk_assistant_id_is_active UNIQUE (assistant_id, is_active)
);
CREATE INDEX CONCURRENTLY index_tenant_id_is_active ON assistant(tenant_id, assistant_id, is_active);


drop table prompts;
create table prompts(
    id uuid PRIMARY KEY NOT NULL,
    tenant_id  varchar(255) NOT NULL,
    assistant_id varchar(255) NOT NULL,
    personality_prompt varchar(5000) not NULL, -- 主要提示词配置
    greeting_prompt  varchar(500) NULL,-- 问候提示词 - 定义如何开始对话
    product_recommendation_prompt varchar(1000) NULL, -- 产品推荐提示词 - 定义如何推荐产品
    objection_handling_prompt varchar(1000) NULL, -- 异议处理提示词 - 定义如何处理客户异议
    closing_prompt varchar(500) NULL,-- 结束对话提示词 - 定义如何结束对话
    context_instructions varchar(1000) NULL, -- 上下文处理指令 - 如何利用历史对话和客户信息
    llm_parameters jsonb, -- LLM生成参数配置
    safety_guidelines jsonb, -- 安全和合规指导原则
    forbidden_topics jsonb, -- 禁止讨论的话题列表
    brand_voice  varchar(500) NULL,-- 品牌声音定义 - 品牌特色和价值观
    product_knowledge varchar(2000) NULL, -- 产品知识要点 - 重点产品信息和卖点
    version bigint not NULL,-- 配置版本
    is_active BOOLEAN NULL DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 使用当前时区的时间戳作为默认值
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 使用当前时区的时间戳作为默认值


    constraint uk_prompts_assistant_id_version_is_active UNIQUE (assistant_id, version, is_active)
);
delete from prompts where assistant_id = 'sales-assistant-1';





create table friends_chat (
    id uuid PRIMARY KEY NOT NULL,
    wechat_code varchar(255) Not Null,
    img_url varchar(1000) NOT NULL,
    friend_code varchar(255) Not Null,
    name varchar(255) Not Null,
    friend_sex varchar(100) not NULL,
    friend_sign varchar(100) not NULL,
    friend_area varchar(100) not NULL,
    call_type boolean not NULL DEFAULT FALSE,
    -- 客户到店进程 是啥？
    remark varchar(1000) NOT NULL,
    add_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, --添加好友的时间，使用当前时区的时间戳作为默认值
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 使用当前时区的时间戳作为默认值
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 使用当前时区的时间戳作为默认值

    constraint uk_tenant_id_is_active UNIQUE (wechat_code, friend_code)
);




